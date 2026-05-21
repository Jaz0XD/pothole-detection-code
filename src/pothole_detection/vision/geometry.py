from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from pothole_detection.config.settings import CameraConfig
from pothole_detection.vision.wireframe import GeometryMetrics


@dataclass(slots=True)
class MetricEstimate:
    distance_m: float
    width_m: float
    length_m: float
    depth_m: float


def _focal_lengths(frame_shape: tuple[int, int, int], camera: CameraConfig) -> tuple[float, float]:
    h, w = frame_shape[:2]
    fx = (w / 2.0) / math.tan(math.radians(camera.horizontal_fov_deg / 2.0))
    fy = (h / 2.0) / math.tan(math.radians(camera.vertical_fov_deg / 2.0))
    return fx, fy


def estimate_metrics(
    frame_shape: tuple[int, int, int],
    bbox: tuple[int, int, int, int],
    geometry: GeometryMetrics,
    camera: CameraConfig,
) -> MetricEstimate:
    h, _ = frame_shape[:2]
    x1, y1, x2, y2 = bbox
    fx, fy = _focal_lengths(frame_shape, camera)

    cy = h / 2.0
    y_bottom = min(max(y2, 0), h - 1)
    pixel_angle = math.atan2((y_bottom - cy), fy)
    ground_angle = math.radians(camera.tilt_down_deg) + pixel_angle
    ground_angle = max(math.radians(2.0), ground_angle)

    distance_m = camera.mount_height_m / math.tan(ground_angle)
    bbox_width_px = max(1, x2 - x1)
    bbox_height_px = max(1, y2 - y1)

    width_m = (bbox_width_px * distance_m) / fx
    length_m = (bbox_height_px * distance_m) / fy
    depth_m = max(0.01, geometry.depth_std * camera.depth_scale_m + geometry.depth_mean * (camera.depth_scale_m / 2.0))

    return MetricEstimate(
        distance_m=float(distance_m),
        width_m=float(width_m),
        length_m=float(length_m),
        depth_m=float(depth_m),
    )


def depth_colormap(depth_map: np.ndarray) -> np.ndarray:
    import cv2

    scaled = np.clip(depth_map * 255.0, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(scaled, cv2.COLORMAP_TURBO)
