from __future__ import annotations

from dataclasses import dataclass

from pothole_detection.config.settings import ControlConfig, SeverityConfig
from pothole_detection.vision.wireframe import GeometryMetrics


@dataclass(slots=True)
class VehicleCommand:
    action: str
    speed: int
    direction: str = "straight"

    def to_line(self) -> str:
        if self.action == "AVOID":
            return f"{self.action} dir={self.direction} speed={self.speed}"
        if self.action in {"CRUISE", "SLOW"}:
            return f"{self.action} speed={self.speed}"
        return "STOP"


def classify_severity(metrics: GeometryMetrics, config: SeverityConfig) -> str:
    if metrics.score >= config.severe_score:
        return "severe"
    if metrics.score >= config.moderate_score:
        return "moderate"
    if metrics.score >= config.minor_score:
        return "minor"
    return "none"


def choose_command(severity: str, metrics: GeometryMetrics, config: ControlConfig) -> VehicleCommand:
    if severity == "severe":
        direction = "left" if metrics.centroid_x_ratio > 0.5 else "right"
        if config.avoid_direction in {"left", "right"}:
            direction = config.avoid_direction
        return VehicleCommand(action="AVOID", speed=config.avoid_speed, direction=direction)
    if severity == "moderate":
        return VehicleCommand(action="SLOW", speed=config.slow_speed)
    if severity == "minor":
        return VehicleCommand(action="CRUISE", speed=config.cruise_speed)
    return VehicleCommand(action="CRUISE", speed=config.cruise_speed)

