from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pothole_detection.config.settings import load_config
from pothole_detection.training.yolo_dataset import initialize_dataset


def main() -> int:
    config = load_config()
    yaml_path = initialize_dataset(config.dataset.root, config.detection.classes)
    print(f"Initialized dataset at {yaml_path.parent}")
    print(f"YOLO config: {yaml_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
