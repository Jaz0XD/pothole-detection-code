from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass(slots=True)
class DetectionTelemetry:
    severity: str = "none"
    score: float = 0.0
    confidence: float = 0.0
    distance_m: float | None = None
    width_m: float | None = None
    length_m: float | None = None
    depth_m: float | None = None


@dataclass(slots=True)
class RuntimeTelemetry:
    timestamp: str = ""
    detection_enabled: bool = True
    command: str = "CRUISE speed=0"
    vehicle_speed_pct: int = 0
    fps: float = 0.0
    detections_seen: int = 0
    top_detection: DetectionTelemetry = field(default_factory=DetectionTelemetry)
    online_samples: int = 0
    retrain_runs: int = 0
    preview_path: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["timestamp"] = self.timestamp or datetime.now(timezone.utc).isoformat()
        return data


class TelemetryWriter:
    def __init__(self, state_path: str | Path) -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, telemetry: RuntimeTelemetry) -> None:
        payload = telemetry.to_dict()
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)
