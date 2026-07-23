import time
import logging
import cv2
import mss
import numpy as np
from src.perceptron.config import DEBUG_VIEW, TARGET_FPS
from src.perceptron.perception.yolo_perception import YOLOPerceptionLayer
from src.perceptron.perception.opencv_perception import OpenCVPerceptionLayer

log = logging.getLogger(__name__)

class PerceptionLayer:
    """Coordinates the YOLO and OpenCV perception layers."""

    def __init__(self, policy_layer):
        self.paused: bool = False
        self.policy_layer = policy_layer
        self.running = False

        self.yolo = (
            YOLOPerceptionLayer(policy_layer)
            if policy_layer.perception_mode in ("yolo", "both")
            else None
        )

        self.opencv = (
            OpenCVPerceptionLayer(policy_layer)
            if policy_layer.perception_mode in ("opencv", "both")
            else None
        )

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

                    active_detections = []
                    annotated_frame = frame.copy()

                    if self.yolo is not None:
                        yolo_detections, results = self.yolo.detect(frame)

                        active_detections.extend(yolo_detections)

                        if DEBUG_VIEW:
                            annotated_frame = self.yolo.annotate(
                                results
                            )

                    if self.opencv is not None:
                        opencv_detections = self.opencv.detect(frame)

                        active_detections.extend(opencv_detections)

                        if DEBUG_VIEW:
                            annotated_frame = self.opencv.annotate(
                                annotated_frame,
                                opencv_detections
                            )

                    self.policy_layer.process_frame_logic(
                        active_detections
                    )

                    if DEBUG_VIEW:
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