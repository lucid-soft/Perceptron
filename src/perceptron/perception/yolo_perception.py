import logging
from ultralytics import YOLO
from src.perceptron.config import MODEL_PATH, CONFIDENCE_THRESHOLD
from src.perceptron.detection import Detection

log = logging.getLogger(__name__)

class YOLOPerceptionLayer:
    """Handles running the YOLO model and reporting detections."""

    def __init__(self, policy_layer):
        self.policy_layer = policy_layer
        self.model = YOLO(MODEL_PATH)

    def detect(self, frame):
        results = self.model.track(
            frame,
            persist=True,
            verbose=False,
            conf=CONFIDENCE_THRESHOLD
        )

        active_detections = []

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            masks = results[0].masks

            for idx, box in enumerate(boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]

                if box.id is not None:
                    track_id = int(box.id[0])
                else:
                    track_id = 1000 + idx

                mask_xy = (
                    masks.xy[idx]
                    if masks is not None
                    else None
                )

                active_detections.append(
                    Detection(
                        id=track_id,
                        label=label,
                        center=(center_x, center_y),
                        box=(x1, y1, x2, y2),
                        mask_xy=mask_xy,
                    )
                )

        return active_detections, results

    def annotate(self, results):
        if not results:
            return None

        return results[0].plot()