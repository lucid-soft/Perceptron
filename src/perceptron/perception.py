import time
import logging
import cv2
import mss
import numpy as np
from ultralytics import YOLO
from src.perceptron.config import DEBUG_VIEW, MODEL_PATH, TARGET_FPS, CONFIDENCE_THRESHOLD
from src.perceptron.detection import Detection

log = logging.getLogger(__name__)

class PerceptionLayer:
    """Handles running the YOLO model and reporting detections to the policy layer."""
    def __init__(self, policy_layer):
        self.paused: bool = False
        self.policy_layer = policy_layer
        self.model = YOLO(MODEL_PATH)
        self.running = False

    def start_loop(self):
        self.running = True
        frame_duration = 1.0 / TARGET_FPS

        log.debug("Starting perception engine...")

        with mss.MSS() as sct:
            try:
                while self.running:
                    if self.paused:
                        time.sleep(0.1)
                        continue

                    start_time = time.monotonic()

                    monitor = self.policy_layer.capture_area
                    screenshot = sct.grab(monitor)

                    frame = np.array(screenshot)[:, :, :3]

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

                    self.policy_layer.process_frame_logic(active_detections)

                    if DEBUG_VIEW:
                        annotated_frame = results[0].plot()

                        cv2.imshow(
                            "Perceptron Debugger View",
                            annotated_frame,
                        )

                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            self.stop()

                    elapsed = time.monotonic() - start_time
                    sleep_time = frame_duration - elapsed

                    if sleep_time > 0:
                        time.sleep(sleep_time)

            finally:
                if DEBUG_VIEW:
                    log.debug("Destroying debugger visual frames...")
                    cv2.destroyAllWindows()

    def stop(self):
        log.debug("Intercepted shutdown signal. Halting loop...")
        self.running = False

    def pause(self):
        self.paused = not self.paused
        if self.paused: cv2.destroyAllWindows()
        log.info(f"Policy {'paused' if self.paused else 'unpaused'}.")