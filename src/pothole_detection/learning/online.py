# Learn from live video feed
# Creates pseudo capture image of potholes

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import threading

import cv2
import numpy as np

from pothole_detection.config.settings import DatasetConfig, OnlineLearningConfig
from pothole_detection.models.detector import Detection


def _write_yolo_label(label_path: Path, detections: list[Detection], frame_shape: tuple[int, int, int]) -> None:
    h, w = frame_shape[:2]
    lines: list[str] = []
    for det in detections:
        x1, y1, x2, y2 = det.bbox
        xc = ((x1 + x2) / 2.0) / w
        yc = ((y1 + y2) / 2.0) / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        lines.append(f"0 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
    label_path.write_text("\n".join(lines), encoding="utf-8")


@dataclass(slots=True)
class OnlineLearningManager:
    dataset_config: DatasetConfig
    learning_config: OnlineLearningConfig
    root: Path = field(init=False)
    pseudo_images: Path = field(init=False)
    pseudo_labels: Path = field(init=False)
    frame_index: int = field(init=False, default=0)
    sample_count: int = field(init=False, default=0)
    retrain_runs: int = field(init=False, default=0)
    _last_retrain_at: datetime = field(init=False, default=datetime.min, repr=False)
    _retrain_lock: threading.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.root = Path(self.dataset_config.root)
        self.pseudo_images = self.root / "images" / "pseudo"
        self.pseudo_labels = self.root / "labels" / "pseudo"
        self.pseudo_images.mkdir(parents=True, exist_ok=True)
        self.pseudo_labels.mkdir(parents=True, exist_ok=True)
        self._retrain_lock = threading.Lock()

    def maybe_capture(self, frame: np.ndarray, detections: list[Detection]) -> None:
        if not (self.learning_config.enabled and self.learning_config.capture_enabled):
            return

        self.frame_index += 1
        if self.frame_index % max(1, self.learning_config.capture_every_n_frames) != 0:
            return

        strong = [det for det in detections if det.confidence >= self.learning_config.min_confidence]
        if not strong:
            return

        stem = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        image_path = self.pseudo_images / f"{stem}{self.dataset_config.image_ext}"
        label_path = self.pseudo_labels / f"{stem}.txt"
        cv2.imwrite(str(image_path), frame)
        _write_yolo_label(label_path, strong, frame.shape)
        self.sample_count += 1

        if self.learning_config.auto_retrain:
            self._maybe_retrain_async()

    def _maybe_retrain_async(self) -> None:
        cooldown = timedelta(minutes=self.learning_config.retrain_cooldown_minutes)
        if self.sample_count < self.learning_config.min_samples_before_retrain:
            return
        if datetime.utcnow() - self._last_retrain_at < cooldown:
            return
        if self._retrain_lock.locked():
            return

        thread = threading.Thread(target=self._run_retrain, daemon=True)
        thread.start()

    def _run_retrain(self) -> None:
        if not self._retrain_lock.acquire(blocking=False):
            return
        try:
            from ultralytics import YOLO

            yaml_path = self.root / "data.yaml"
            if not yaml_path.exists():
                return

            model = YOLO(self.learning_config.base_weights)
            model.train(
                data=str(yaml_path),
                epochs=self.learning_config.epochs,
                imgsz=self.learning_config.imgsz,
                project=self.learning_config.project_dir,
                name="online",
                exist_ok=True,
            )
            self.retrain_runs += 1
            self._last_retrain_at = datetime.utcnow()
        except Exception as exc:
            print(f"[ONLINE-LEARNING] retrain skipped: {exc}")
        finally:
            self._retrain_lock.release()
