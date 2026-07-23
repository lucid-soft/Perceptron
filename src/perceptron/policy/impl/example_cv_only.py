import time
import logging
from src.perceptron.policy.base import BasePolicy
from src.perceptron.policy.frame import FrameData

log = logging.getLogger(__name__)

class ExampleCVOnlyPolicy(BasePolicy):
    """Extremely basic example policy that only uses OpenCV instead of YOLO."""
    def __init__(self, action_layer, capture_area):
        super().__init__(action_layer, capture_area)

        # self.monitored_labels = [] <- Already initialized in base class so we don't need this line if we aren't using it
        self.monitored_images = ["example", "example_2", "example_3"] # names from /assets/images/ without the .png

        self.perception_mode = "opencv" # This part tells what perception systems you're using.

    def process_frame_logic(self, active_detections):
        frame = FrameData(
            active_detections,
            center=(self.center_x, self.center_y),
        ) # This is what we can query for detections to click on

        for name in self.monitored_images:
            target = frame.closest(name) # grabs the closest detection for that name from the center of capture area
            if target is not None:
                log.debug(f"Found Example ID: {target.id}. Clicking...")
                self.action_layer.humanized_click(target)