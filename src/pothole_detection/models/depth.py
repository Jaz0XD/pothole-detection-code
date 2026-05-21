# MiDAS and DepthAnything pipeline integration

from __future__ import annotations

from typing import Protocol

import cv2
import numpy as np

from pothole_detection.config.settings import DepthConfig


class DepthEstimator(Protocol):
    def estimate(self, frame: np.ndarray) -> np.ndarray:
        ...


def _normalize_map(depth: np.ndarray) -> np.ndarray:
    return cv2.normalize(depth.astype(np.float32), None, 0.0, 1.0, cv2.NORM_MINMAX)


class ProxyDepthEstimator:
    def __init__(self, config: DepthConfig) -> None:
        self.config = config

    def estimate(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        blur = cv2.GaussianBlur(gray, (21, 21), 0)
        lap = cv2.Laplacian(blur, cv2.CV_32F, ksize=3)
        depth = -lap + (1.0 - blur)
        return _normalize_map(depth)


class MiDaSDepthEstimator:
    def __init__(self, config: DepthConfig) -> None:
        self.config = config
        self._model = None
        self._transform = None
        self._device = None

    def _load(self) -> None:
        if self._model is not None:
            return

        import torch

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model = torch.hub.load("intel-isl/MiDaS", self.config.midas_model_type)
        self._model.to(self._device)
        self._model.eval()
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        if self.config.midas_model_type in {"DPT_Large", "DPT_Hybrid"}:
            self._transform = midas_transforms.dpt_transform
        else:
            self._transform = midas_transforms.small_transform

    def estimate(self, frame: np.ndarray) -> np.ndarray:
        self._load()

        import torch

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        batch = self._transform(rgb).to(self._device)
        with torch.no_grad():
            prediction = self._model(batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=rgb.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        return _normalize_map(prediction.cpu().numpy())


class DepthAnythingEstimator:
    def __init__(self, config: DepthConfig) -> None:
        self.config = config
        self._pipeline = None

    def _load(self) -> None:
        if self._pipeline is not None:
            return

        from transformers import pipeline

        self._pipeline = pipeline(task="depth-estimation", model=self.config.depthanything_model)

    def estimate(self, frame: np.ndarray) -> np.ndarray:
        self._load()

        from PIL import Image

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        result = self._pipeline(pil)
        predicted = np.array(result["depth"], dtype=np.float32)
        resized = cv2.resize(predicted, (frame.shape[1], frame.shape[0]))
        return _normalize_map(resized)


class HybridDepthEstimator:
    def __init__(self, estimators: list[DepthEstimator]) -> None:
        self.estimators = estimators

    def estimate(self, frame: np.ndarray) -> np.ndarray:
        outputs = [_normalize_map(est.estimate(frame)) for est in self.estimators]
        if not outputs:
            raise RuntimeError("HybridDepthEstimator requires at least one estimator")
        return _normalize_map(np.mean(outputs, axis=0))


def build_depth_estimator(config: DepthConfig) -> DepthEstimator:
    mode = config.mode.lower()
    if mode == "midas":
        return MiDaSDepthEstimator(config)
    if mode == "depthanything":
        return DepthAnythingEstimator(config)
    if mode == "hybrid":
        estimators: list[DepthEstimator] = [ProxyDepthEstimator(config)]
        try:
            estimators.append(MiDaSDepthEstimator(config))
        except Exception:
            pass
        try:
            estimators.append(DepthAnythingEstimator(config))
        except Exception:
            pass
        return HybridDepthEstimator(estimators)
    return ProxyDepthEstimator(config)
