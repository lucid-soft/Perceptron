import time
import logging
from .base import BasePolicy
from .frame import FrameData

log = logging.getLogger(__name__)

class ExampleCVOnlyPolicy(BasePolicy):
    """Extremely basic example policy that only uses OpenCV instead of YOLO."""
    def __init__(self, action_layer, capture_area):
        super().__init__(action_layer, capture_area)

        self.monitored_labels = []
        self.monitored_images = ["example", "example_2", "example_3"]

        self.last_click_time = time.monotonic()
        self.perception_mode = "opencv"

    def process_frame_logic(self, active_detections):
        frame = FrameData(
            active_detections,
            center=(self.center_x, self.center_y),
        )

        for name in self.monitored_images:
            target = frame.closest(name)
            if target is not None:
                log.debug(f"Found Example ID: {target.id}. Clicking...")
                self.action_layer.humanized_click(target)