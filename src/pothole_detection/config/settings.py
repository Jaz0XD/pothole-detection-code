#Configuring Component values

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(slots=True)
class VideoConfig:
    source: str = "http://192.168.1.100/cam-hi.jpg"
    display: bool = True
    frame_width: int = 960
    frame_height: int = 540


@dataclass(slots=True)
class CameraConfig:
    horizontal_fov_deg: float = 120.0
    vertical_fov_deg: float = 78.0
    mount_height_m: float = 0.14
    tilt_down_deg: float = 18.0
    depth_scale_m: float = 0.18


@dataclass(slots=True)
class RuntimeConfig:
    enable_detection: bool = True
    max_detections: int = 3


@dataclass(slots=True)
class DetectionConfig:
    mode: str = "heuristic"
    confidence: float = 0.35
    min_area: int = 900
    roi_start_ratio: float = 0.45
    classes: list[str] | None = None


@dataclass(slots=True)
class DepthConfig:
    mode: str = "proxy"
    normalize: bool = True
    midas_model_type: str = "DPT_Hybrid"
    depthanything_model: str = "LiheYoung/depth-anything-small-hf"


@dataclass(slots=True)
class SeverityConfig:
    minor_score: float = 0.12
    moderate_score: float = 0.24
    severe_score: float = 0.40


@dataclass(slots=True)
class ControlConfig:
    cruise_speed: int = 55
    slow_speed: int = 30
    avoid_speed: int = 24
    avoid_direction: str = "right"
    send_interval_ms: int = 150


@dataclass(slots=True)
class DatasetConfig:
    root: str = "datasets/pothole_yolo"
    train_split: float = 0.8
    val_split: float = 0.1
    test_split: float = 0.1
    image_ext: str = ".jpg"


@dataclass(slots=True)
class OnlineLearningConfig:
    enabled: bool = True
    capture_enabled: bool = True
    auto_retrain: bool = False
    min_confidence: float = 0.80
    capture_every_n_frames: int = 15
    min_samples_before_retrain: int = 50
    retrain_cooldown_minutes: int = 30
    epochs: int = 5
    imgsz: int = 640
    base_weights: str = "weights/yolov8n-seg.pt"
    project_dir: str = "artifacts/training"


@dataclass(slots=True)
class DashboardConfig:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8765
    show_preview: bool = False
    write_snapshot: bool = True
    snapshot_path: str = "artifacts/dashboard/frame.jpg"
    state_path: str = "artifacts/dashboard/state.json"


@dataclass(slots=True)
class AppConfig:
    video: VideoConfig
    camera: CameraConfig
    runtime: RuntimeConfig
    detection: DetectionConfig
    depth: DepthConfig
    severity: SeverityConfig
    control: ControlConfig
    dataset: DatasetConfig
    online_learning: OnlineLearningConfig
    dashboard: DashboardConfig


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path else Path(__file__).with_name("default.toml")
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    return AppConfig(
        video=VideoConfig(**raw.get("video", {})),
        camera=CameraConfig(**raw.get("camera", {})),
        runtime=RuntimeConfig(**raw.get("runtime", {})),
        detection=DetectionConfig(**raw.get("detection", {})),
        depth=DepthConfig(**raw.get("depth", {})),
        severity=SeverityConfig(**raw.get("severity", {})),
        control=ControlConfig(**raw.get("control", {})),
        dataset=DatasetConfig(**raw.get("dataset", {})),
        online_learning=OnlineLearningConfig(**raw.get("online_learning", {})),
        dashboard=DashboardConfig(**raw.get("dashboard", {})),
    )
