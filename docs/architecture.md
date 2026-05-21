# Architecture

## Runtime flow

1. `capture`
   - Read frames from webcam, video file, or ESP32-CAM stream.
2. `detect`
   - Produce pothole regions using a heuristic detector now or YOLO later.
3. `depth`
   - Estimate a depth-like map from monocular RGB input.
4. `wireframe`
   - Sample the pothole region and draw vertical depth cues.
5. `severity`
   - Score the pothole using area, depth deviation, and shape cues.
6. `control`
   - Convert severity into `CRUISE`, `SLOW`, or `AVOID`.
7. `actuation`
   - Send commands to the motor-control ESP32 over serial.

## Practical hardware topology

### Option A: easiest prototype

- `ESP32-CAM` streams frames over Wi-Fi
- Laptop runs Python inference
- Laptop sends commands to second `ESP32` over USB serial
- Second `ESP32` controls DC motors and steering servo

### Option B: embedded prototype

- `ESP32-CAM` streams frames to a `Jetson Nano`
- Jetson runs the Python pipeline
- Jetson sends commands to a motor-control ESP32 or directly to motor drivers

## Why this separation matters

Running the vision stack on the same microcontroller that handles low-level motor timing is not a good first prototype. Perception latency, Wi-Fi instability, and motor-control jitter are easier to manage when:

- Python handles perception and decision logic
- ESP32 handles deterministic actuation

