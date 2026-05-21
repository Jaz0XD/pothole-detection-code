from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from pothole_detection.models.detector import Detection


@dataclass(slots=True)
class GeometryMetrics:
    area_ratio: float
    depth_mean: float
    depth_std: float
    shape_irregularity: float
    centroid_x_ratio: float
    score: float


def analyze_detection(frame: np.ndarray, depth_map: np.ndarray, detection: Detection) -> GeometryMetrics:
    mask = detection.mask > 0
    h, w = frame.shape[:2]
    area_ratio = float(mask.sum()) / float(h * w)

    depth_values = depth_map[mask]
    if depth_values.size == 0:
        return GeometryMetrics(0.0, 0.0, 0.0, 0.0, 0.5, 0.0)

    contours, _ = cv2.findContours(detection.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    irregularity = 0.0
    centroid_x_ratio = 0.5
    if contours:
        contour = max(contours, key=cv2.contourArea)
        perimeter = cv2.arcLength(contour, True)
        area = max(cv2.contourArea(contour), 1.0)
        irregularity = float((perimeter * perimeter) / (4.0 * np.pi * area))
        moments = cv2.moments(contour)
        if moments["m00"] > 0:
            centroid_x_ratio = float(moments["m10"] / moments["m00"]) / float(w)

    depth_mean = float(depth_values.mean())
    depth_std = float(depth_values.std())
    score = (0.55 * depth_mean) + (0.30 * min(depth_std * 2.0, 1.0)) + (0.15 * min(area_ratio * 8.0, 1.0))

    return GeometryMetrics(
        area_ratio=area_ratio,
        depth_mean=depth_mean,
        depth_std=depth_std,
        shape_irregularity=irregularity,
        centroid_x_ratio=centroid_x_ratio,
        score=score,
    )


def overlay_wireframe(frame: np.ndarray, depth_map: np.ndarray, mask: np.ndarray, step: int = 18) -> np.ndarray:
    output = frame.copy()
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return output

    sampled = list(zip(xs[::step], ys[::step]))
    for x, y in sampled:
        z = depth_map[y, x]
        top = max(0, int(y - (10 + z * 25)))
        color = (0, int(120 + z * 135), 255)
        cv2.line(output, (x, y), (x, top), color, 1, lineType=cv2.LINE_AA)
        cv2.circle(output, (x, top), 1, color, -1, lineType=cv2.LINE_AA)

    for idx in range(1, len(sampled)):
        x1, y1 = sampled[idx - 1]
        x2, y2 = sampled[idx]
        z1 = depth_map[y1, x1]
        z2 = depth_map[y2, x2]
        p1 = (x1, max(0, int(y1 - (10 + z1 * 25))))
        p2 = (x2, max(0, int(y2 - (10 + z2 * 25))))
        cv2.line(output, p1, p2, (255, 180, 40), 1, lineType=cv2.LINE_AA)

    return output
