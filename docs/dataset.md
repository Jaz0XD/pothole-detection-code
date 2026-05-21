# Dataset Notes

## Recommended data mix

Use a mix of:

- public pothole datasets
- your own road footage
- frames captured from the actual `ESP32-CAM` mounting angle

## File format

For YOLO training:

- image files: `jpg` or `png`
- label files: `.txt`
- one label file per image

Example:

```text
frame_0001.jpg
frame_0001.txt
```

Example label:

```text
0 0.544531 0.682407 0.221875 0.172222
```

## Online data capture

High-confidence live detections are written to the `pseudo` split. Treat those as a review queue first. If pseudo labels are wrong, retraining will reinforce the wrong features.

## Metric estimation limits

Distance, width, length, and depth from a single camera are only approximate until you calibrate:

- real field of view
- mounting height
- camera tilt angle
- depth scale factor
