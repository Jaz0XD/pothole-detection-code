# YOLO inference load / predict

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from pothole_detection.config.settings import DetectionConfig


@dataclass(slots=True)
class Detection:
    bbox: tuple[int, int, int, int]
    confidence: float
    mask: np.ndarray
    label: str = "pothole"


class Detector(Protocol):
    def detect(self, frame: np.ndarray) -> list[Detection]:
        ...


class HeuristicPotholeDetector:
    def __init__(self, config: DetectionConfig) -> None:
        self.config = config

    def detect(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2]
        roi_y = int(h * self.config.roi_start_ratio)
        roi = frame[roi_y:, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (7, 7), 0)
        blackhat = cv2.morphologyEx(
            blur,
            cv2.MORPH_BLACKHAT,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)),
        )
        thresh = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        thresh = cv2.medianBlur(thresh, 5)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections: list[Detection] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.config.min_area:
                continue

            x, y, bw, bh = cv2.boundingRect(contour)
            full_y = y + roi_y

            mask = np.zeros((h, w), dtype=np.uint8)
            shifted = contour.copy()
            shifted[:, :, 1] += roi_y
            cv2.drawContours(mask, [shifted], -1, 255, thickness=-1)

            confidence = min(0.95, 0.35 + (area / float(w * h)))
            detections.append(
                Detection(
                    bbox=(x, full_y, x + bw, full_y + bh),
                    confidence=confidence,
                    mask=mask,
                )
            )

        detections.sort(key=lambda item: item.confidence, reverse=True)
        return detections


class OptionalYoloDetector:
    def __init__(self, weights_path: str, confidence: float = 0.35) -> None:
        self.confidence = confidence
        self.weights_path = Path(weights_path)
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from ultralytics import YOLO

        self._model = YOLO(str(self.weights_path))

    def detect(self, frame: np.ndarray) -> list[Detection]:
        self._load()
        results = self._model.predict(frame, conf=self.confidence, verbose=False)
        detections: list[Detection] = []

        if not results:
            return detections

        result = results[0]
        boxes = result.boxes
        masks = result.masks
        if boxes is None:
            return detections

        mask_data = masks.data.cpu().numpy() if masks is not None else None
        h, w = frame.shape[:2]

        for idx, box in enumerate(boxes):
            xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
            conf = float(box.conf[0].cpu().numpy())
            mask = np.zeros((h, w), dtype=np.uint8)

            if mask_data is not None and idx < len(mask_data):
                resized = cv2.resize(mask_data[idx], (w, h))
                mask = (resized > 0.5).astype(np.uint8) * 255
            else:
                x1, y1, x2, y2 = xyxy
                mask[y1:y2, x1:x2] = 255

            detections.append(Detection(bbox=tuple(xyxy), confidence=conf, mask=mask))

        return detections


def build_detector(config: DetectionConfig, model_path: str | None = None) -> Detector:
    if config.mode == "yolo" and model_path:
        return OptionalYoloDetector(model_path, confidence=config.confidence)
    return HeuristicPotholeDetector(config)

