# Perceptron

Perceptron is a computer vision framework for building game automation using object detection and tracking.

The project separates perception, decision-making, and hardware interaction into independent layers so new behaviors can be added without touching the rest of the system.

The included example policy automates combat against Hill Giants in Old School RuneScape, but the architecture is intended to support other policies and games with minimal changes.

---

## Features

- YOLO-based object detection
- Persistent object tracking with ByteTrack
- Policy-based behavior system
- Humanized mouse movement and click selection
- Segmentation mask-aware click targeting
- Toggleable debug visualization

---

## How It Works

Each frame follows the same pipeline:

1. The perception layer is responsible only for identifying objects on screen.

2. Policies receive those detections and decide what to do with them.

3. The action layer handles all hardware interaction, including randomized click placement inside segmentation masks for more natural behavior.

---

## Configuration

Most settings can be changed in `config.py`.

---

## Adding a New Policy

Create a new policy that inherits from `BasePolicy` and implement `process_frame_logic()`.

```python
class MyPolicy(BasePolicy):
    def process_frame_logic(self, detections):
        ...
```

Register it in `policy/__init__.py`:

```python
POLICIES = {
    "my_policy": MyPolicy,
}
```

Then set it as the active policy in `config.py`.

---

## Requirements

- Python 3.11+
- Windows 10/11

A trained YOLO segmentation model is expected at (can also use .onnx format as well):

```
assets/models/example-seg.pt 
```
**Non-segmentation YOLO models can also be used, but will use the fallback hitbox clicking**

---

## Current Example

The included policy demonstrates:

- locating the nearest Hill Giant
- clicking a randomized point inside the segmentation mask
- tracking the selected target
- detecting combat using hit markers
- returning to the search state when combat ends
---