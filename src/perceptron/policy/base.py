from enum import Enum, auto

class BotState(Enum):
    SEARCHING = auto()
    ENGAGING = auto()
    COMBAT = auto()


class BasePolicy:
    def __init__(self, action_layer, capture_area):
        self.action_layer = action_layer
        self.capture_area = capture_area

        self.center_x = capture_area["width"] // 2
        self.center_y = capture_area["height"] // 2

        self.monitored_labels = []
        self.monitored_images = []
        # "yolo", "opencv", or "both"
        self.perception_mode = "none" # doesn't load either by default, specify in policy init

    def process_frame_logic(self, active_detections):
        raise NotImplementedError(
            "Subclasses must implement process_frame_logic()!"
        )