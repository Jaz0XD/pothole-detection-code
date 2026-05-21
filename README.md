# Pothole Detection RC Car Prototype

This repository supports four connected workflows:

- train a `YOLOv8` pothole model on a proper dataset
- run real-time detection from a single camera or `ESP32-CAM`
- estimate pothole distance, width, length, and depth using monocular depth plus wireframe cues
- capture high-confidence live detections for pseudo-labeled self-training

## Core pipeline

1. frame capture
2. YOLO or heuristic pothole detection
3. depth estimation with `MiDaS`, `Depth Anything`, `hybrid`, or `proxy`
4. wireframe mesh overlay
5. geometric estimation
6. severity and control policy
7. online sample capture and telemetry dashboard

## Dataset format

The training dataset uses YOLO layout under [datasets/pothole_yolo](/home/sirajuddeen/PROJECTS/pothole-detection/datasets/pothole_yolo):

```text
datasets/pothole_yolo/
├── data.yaml
├── images/
│   ├── train/
│   ├── val/
│   ├── test/
│   └── pseudo/
└── labels/
    ├── train/
    ├── val/
    ├── test/
    └── pseudo/
```

YOLO label file format:

```text
class_id x_center y_center width height
```

All coordinates except `class_id` are normalized.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install ultralytics pyserial torch torchvision transformers pillow
python scripts/init_dataset.py
```

## Train a base model

Place your labeled pothole images and labels into `images/train`, `labels/train`, `images/val`, and `labels/val`.

Bounding-box model:

```bash
yolo task=detect mode=train model=yolov8n.pt data=datasets/pothole_yolo/data.yaml epochs=50 imgsz=640
```

Segmentation model:

```bash
yolo task=segment mode=train model=yolov8n-seg.pt data=datasets/pothole_yolo/data.yaml epochs=50 imgsz=640
```

## Run real-time inference

Webcam:

```bash
python app.py --source 0 --model-path runs/detect/train/weights/best.pt
```

ESP32-CAM:

```bash
python app.py --source http://192.168.137.95/stream --model-path runs/detect/train/weights/best.pt
```

Telemetry-only dashboard:

```bash
python app.py --source 0 --model-path runs/detect/train/weights/best.pt --telemetry-only
```

Detection disabled but dashboard still active:

```bash
python app.py --source 0 --disable-detection --telemetry-only
```

## Self-training

When `online_learning.enabled=true`, high-confidence detections are saved into:

- `datasets/pothole_yolo/images/pseudo`
- `datasets/pothole_yolo/labels/pseudo`

Automatic retraining is available but disabled by default because pseudo-label drift can hurt accuracy if you do not review the captured samples.

## Dashboard

The dashboard exposes:

- detection enabled/disabled state
- commanded vehicle speed
- pothole distance
- estimated width, length, and depth
- online-learning sample count

Default URL:

```text
http://127.0.0.1:8765
```

## Key files

- [src/pothole_detection/app.py](/home/sirajuddeen/PROJECTS/pothole-detection/src/pothole_detection/app.py)
- [src/pothole_detection/models/depth.py](/home/sirajuddeen/PROJECTS/pothole-detection/src/pothole_detection/models/depth.py)
- [src/pothole_detection/vision/geometry.py](/home/sirajuddeen/PROJECTS/pothole-detection/src/pothole_detection/vision/geometry.py)
- [src/pothole_detection/learning/online.py](/home/sirajuddeen/PROJECTS/pothole-detection/src/pothole_detection/learning/online.py)
- [src/pothole_detection/dashboard/server.py](/home/sirajuddeen/PROJECTS/pothole-detection/src/pothole_detection/dashboard/server.py)
