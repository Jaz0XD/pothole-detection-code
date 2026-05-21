# The main app.py file

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from pothole_detection.app import main
except ModuleNotFoundError as exc:
    missing = exc.name or "dependency"

    def main() -> int:
        print(f"Missing dependency: {missing}")
        print("Install project dependencies first, for example:")
        print("  pip install -e .")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
