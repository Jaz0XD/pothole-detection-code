from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import time

from pothole_detection.config.settings import load_config
from pothole_detection.control.policy import choose_command, classify_severity
from pothole_detection.control.serial_bridge import SerialBridge
from pothole_detection.dashboard.server import DashboardServer
from pothole_detection.learning.online import OnlineLearningManager
from pothole_detection.models.depth import build_depth_estimator
from pothole_detection.models.detector import build_detector
from pothole_detection.telemetry import DetectionTelemetry, RuntimeTelemetry, TelemetryWriter
from pothole_detection.training.yolo_dataset import initialize_dataset
from pothole_detection.vision.capture import open_video_source
from pothole_detection.vision.geometry import depth_colormap, estimate_metrics
from pothole_detection.vision.wireframe import GeometryMetrics, analyze_detection, overlay_wireframe


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Real-time pothole detection and telemetry pipeline")
    parser.add_argument("--source", default=None, help="Camera index, video path, ESP32-CAM MJPEG URL, or ESP32-CAM JPEG endpoint like http://IP/cam-hi.jpg")
    parser.add_argument("--config", default=None, help="Path to TOML configuration file")
    parser.add_argument("--model-path", default=None, help="Path to YOLO weights when detection.mode=yolo")
    parser.add_argument("--serial-port", default=None, help="Serial port for ESP32 motor controller")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baudrate")
    parser.add_argument("--save-output", default=None, help="Optional output video path")
    parser.add_argument("--telemetry-only", action="store_true", help="Disable camera preview and keep only telemetry/dashboard output")
    parser.add_argument("--disable-detection", action="store_true", help="Skip pothole inference but keep telemetry and speed reporting active")
    return parser


def format_metric(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def draw_panel(frame, telemetry: RuntimeTelemetry, fps: float) -> None:
    import cv2

    cv2.rectangle(frame, (10, 10), (520, 148), (20, 20, 20), -1)
    cv2.putText(frame, f"Detection: {'on' if telemetry.detection_enabled else 'off'}", (22, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Severity: {telemetry.top_detection.severity}", (22, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 235, 255), 2)
    cv2.putText(frame, f"Distance: {format_metric(telemetry.top_detection.distance_m)} m", (22, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 255, 180), 2)
    cv2.putText(frame, f"Width/Length/Depth: {format_metric(telemetry.top_detection.width_m)}/{format_metric(telemetry.top_detection.length_m)}/{format_metric(telemetry.top_detection.depth_m)} m", (22, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (180, 255, 180), 2)
    cv2.putText(frame, f"Cmd: {telemetry.command}", (22, 134), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 220, 120), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (410, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 220, 120), 2)


def default_metrics() -> GeometryMetrics:
    return GeometryMetrics(
        area_ratio=0.0,
        depth_mean=0.0,
        depth_std=0.0,
        shape_irregularity=0.0,
        centroid_x_ratio=0.5,
        score=0.0,
    )


def main() -> int:
    import cv2

    args = build_arg_parser().parse_args()
    config = load_config(args.config)
    source = args.source or config.video.source
    detection_enabled = config.runtime.enable_detection and not args.disable_detection
    if args.telemetry_only:
        config.video.display = False

    initialize_dataset(config.dataset.root, config.detection.classes)

    try:
        cap = open_video_source(source)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1
    detector = build_detector(config.detection, args.model_path)
    depth_estimator = build_depth_estimator(config.depth)
    serial_bridge = SerialBridge(args.serial_port, baudrate=args.baudrate, min_interval_ms=config.control.send_interval_ms)
    learning = OnlineLearningManager(config.dataset, config.online_learning)
    telemetry_writer = TelemetryWriter(config.dashboard.state_path)
    dashboard = DashboardServer(config.dashboard)
    dashboard.start()

    snapshot_path = Path(config.dashboard.snapshot_path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    writer = None
    if args.save_output:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.save_output, fourcc, 20.0, (config.video.frame_width, config.video.frame_height))

    last_time = time.time()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.resize(frame, (config.video.frame_width, config.video.frame_height))
            annotated = frame.copy()
            telemetry = RuntimeTelemetry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                detection_enabled=detection_enabled,
                command="CRUISE speed=0",
                vehicle_speed_pct=config.control.cruise_speed,
                preview_path=str(snapshot_path) if config.dashboard.write_snapshot and config.dashboard.show_preview else None,
            )

            if detection_enabled:
                depth_map = depth_estimator.estimate(frame)
                detections = detector.detect(frame)
                telemetry.detections_seen = len(detections)
                best_score = 0.0
                best_command = None
                best_detection = DetectionTelemetry()

                for detection in detections[: config.runtime.max_detections]:
                    geometry = analyze_detection(frame, depth_map, detection)
                    severity = classify_severity(geometry, config.severity)
                    metric = estimate_metrics(frame.shape, detection.bbox, geometry, config.camera)
                    command = choose_command(severity, geometry, config.control)

                    if geometry.score >= best_score:
                        best_score = geometry.score
                        best_command = command
                        best_detection = DetectionTelemetry(
                            severity=severity,
                            score=geometry.score,
                            confidence=detection.confidence,
                            distance_m=metric.distance_m,
                            width_m=metric.width_m,
                            length_m=metric.length_m,
                            depth_m=metric.depth_m,
                        )

                    x1, y1, x2, y2 = detection.bbox
                    color = (0, 255, 0) if severity in {"none", "minor"} else (0, 215, 255) if severity == "moderate" else (0, 0, 255)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        annotated,
                        f"{severity} d={metric.distance_m:.2f}m",
                        (x1, max(24, y1 - 12)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.58,
                        color,
                        2,
                    )
                    annotated = overlay_wireframe(annotated, depth_map, detection.mask)

                learning.maybe_capture(frame, detections)
                telemetry.online_samples = learning.sample_count
                telemetry.retrain_runs = learning.retrain_runs
                telemetry.top_detection = best_detection

                if best_command is None:
                    best_command = choose_command("none", default_metrics(), config.control)
                telemetry.command = best_command.to_line()
                telemetry.vehicle_speed_pct = best_command.speed
                serial_bridge.send(best_command)

                small_depth = cv2.resize(depth_colormap(depth_map), (240, 135))
                annotated[config.video.frame_height - 145 : config.video.frame_height - 10, 10:250] = small_depth
            else:
                command = choose_command("none", default_metrics(), config.control)
                telemetry.command = command.to_line()
                telemetry.vehicle_speed_pct = command.speed
                serial_bridge.send(command)
                cv2.putText(annotated, "Detection disabled - telemetry only", (22, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 220, 120), 2)

            fps = 1.0 / max(time.time() - last_time, 1e-6)
            last_time = time.time()
            telemetry.fps = fps
            draw_panel(annotated, telemetry, fps)
            telemetry_writer.write(telemetry)

            if writer:
                writer.write(annotated)
            if config.dashboard.write_snapshot and config.dashboard.show_preview:
                cv2.imwrite(str(snapshot_path), annotated)

            if config.video.display:
                cv2.imshow("Pothole Detection Prototype", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key in {27, ord("q")}:
                    break
    finally:
        cap.release()
        if writer:
            writer.release()
        serial_bridge.close()
        dashboard.stop()
        cv2.destroyAllWindows()

    return 0
