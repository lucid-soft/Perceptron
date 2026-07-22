import logging
from pathlib import Path
import cv2
import numpy as np
from src.perceptron.config import IMAGE_PATH, OPENCV_MATCH_THRESHOLD
from src.perceptron.detection import Detection

log = logging.getLogger(__name__)

class OpenCVPerceptionLayer:
    """Handles OpenCV image detection and reporting detections."""

    def __init__(self, policy_layer):
        self.policy_layer = policy_layer
        self.templates = {}

        self._load_templates()

    def _load_templates(self):
        for image_name in self.policy_layer.monitored_images:
            image_path = Path(IMAGE_PATH) / f"{image_name}.png"

            template = cv2.imread(str(image_path), cv2.IMREAD_COLOR)

            if template is None:
                log.warning(f"Could not load OpenCV image: {image_path}")
                continue

            self.templates[image_name] = template

    def detect(self, frame):
        active_detections = []

        for image_name, template in self.templates.items():
            template_height, template_width = template.shape[:2]
            frame_height, frame_width = frame.shape[:2]

            if template_width > frame_width or template_height > frame_height:
                log.warning(f"OpenCV image '{image_name}' is larger than the captured frame.")
                continue

            result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)

            locations = np.where(result >= OPENCV_MATCH_THRESHOLD)

            boxes = []
            confidences = []

            for y, x in zip(locations[0], locations[1]):
                boxes.append([
                    int(x),
                    int(y),
                    int(template_width),
                    int(template_height),
                ])

                confidences.append(float(result[y, x]))

            if not boxes:
                continue

            indices = cv2.dnn.NMSBoxes(boxes, confidences, OPENCV_MATCH_THRESHOLD,0.3)

            for idx in indices:
                idx = int(idx)

                x, y, width, height = boxes[idx]

                x1 = x
                y1 = y
                x2 = x + width
                y2 = y + height

                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                track_id = hash(
                    (image_name, x1, y1)
                ) & 0x7FFFFFFF

                active_detections.append(
                    Detection(
                        id=track_id,
                        label=image_name,
                        center=(center_x, center_y),
                        box=(x1, y1, x2, y2),
                        mask_xy=None,
                    )
                )

        return active_detections

    def annotate(self, frame, detections):
        annotated_frame = frame.copy()

        for detection in detections:
            x1, y1, x2, y2 = detection.box

            cv2.rectangle(
                annotated_frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.putText(
                annotated_frame,
                detection.label,
                (x1, max(0, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )

        return annotated_frame