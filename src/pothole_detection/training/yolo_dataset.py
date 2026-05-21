# YOLO Training the dataset /w 50 epochs

from __future__ import annotations
from pathlib import Path

from pothole_detection.config.settings import DatasetConfig


SPLITS = ("train", "val", "test")


def initialize_dataset(root: str | Path, classes: list[str] | None = None) -> Path:
    dataset_root = Path(root)
    for prefix in ("images", "labels"):
        for split in SPLITS:
            (dataset_root / prefix / split).mkdir(parents=True, exist_ok=True)
        (dataset_root / prefix / "pseudo").mkdir(parents=True, exist_ok=True)

    names = classes or ["pothole"]
    yaml_body = "\n".join(
        [
            f"path: {dataset_root.resolve()}",
            "train: images/train",
            "val: images/val",
            "test: images/test",
            "",
            f"names: {names}",
        ]
    )
    yaml_path = dataset_root / "data.yaml"
    yaml_path.write_text(yaml_body + "\n", encoding="utf-8")
    readme = dataset_root / "README.md"
    if not readme.exists():
        readme.write_text(
            "# YOLO Dataset\n\n"
            "Store road frames in `images/<split>` and matching YOLO label files in `labels/<split>`.\n"
            "Each label line must follow `class x_center y_center width height` with normalized values.\n",
            encoding="utf-8",
        )
    return yaml_path


def training_command(config: DatasetConfig, weights: str, epochs: int = 50, imgsz: int = 640) -> str:
    yaml_path = Path(config.root) / "data.yaml"
    return f"yolo task=detect mode=train model={weights} data={yaml_path} epochs={epochs} imgsz={imgsz}"
