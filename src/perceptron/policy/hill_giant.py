import time
import logging
from .base import BasePolicy, BotState
from .frame import FrameData

log = logging.getLogger(__name__)

class HillGiantPolicy(BasePolicy):
    """Example policy that kills hill giants in runescape and nothing else."""
    COMBAT_COOLDOWN_SECONDS = 6.0

    def __init__(self, action_layer, capture_area):
        super().__init__(action_layer, capture_area)

        self.monitored_labels = [
            "hill_giant",
            "hit_marker",
        ]

        self.monitored_images = []
        self.perception_mode = "yolo" # Can also use "both", or just "opencv"
        self.state = BotState.SEARCHING
        self.target_id = None

        self.state_enter_time = time.monotonic()
        self.last_hit_time = 0.0

        self.processed_hit_markers = set()

    def _transition_to(self, new_state):
        log.debug(f"[FSM] Transition: {self.state.name} -> {new_state.name}")

        self.state = new_state
        self.state_enter_time = time.monotonic()

    def process_frame_logic(self, active_detections):
        frame = FrameData(
            active_detections,
            center=(self.center_x, self.center_y),
        )

        if self.state == BotState.SEARCHING:
            self._handle_searching(frame)

        elif self.state == BotState.ENGAGING:
            self._handle_engaging(frame)

        elif self.state == BotState.COMBAT:
            self._handle_combat(frame)

    def _handle_searching(self, frame):
        target = frame.closest("hill_giant")

        if target is None:
            return

        log.debug(f"Acquired Giant ID: {target.id}. Clicking...")

        self.action_layer.humanized_click(target)

        self.target_id = target.id

        self._transition_to(BotState.ENGAGING)

    def _handle_engaging(self, frame):
        time_in_state = time.monotonic() - self.state_enter_time

        if self._sees_hit_marker_on_target(frame):
            self.last_hit_time = time.monotonic()
            self._transition_to(BotState.COMBAT)
            return

        if (
                frame.by_id(self.target_id) is None
                or time_in_state > self.COMBAT_COOLDOWN_SECONDS
        ):
            log.debug("Engage failed. Resetting.")

            self.target_id = None
            self._transition_to(BotState.SEARCHING)

    def _handle_combat(self, frame):
        if frame.by_id(self.target_id) is None:
            log.debug("Target defeated.")

            self.target_id = None
            self._transition_to(BotState.SEARCHING)
            return

        if self._sees_hit_marker_on_target(frame):
            self.last_hit_time = time.monotonic()

        if time.monotonic() - self.last_hit_time > 4.0:
            log.debug("Combat idle.")

            self.target_id = None
            self._transition_to(BotState.SEARCHING)

    def _sees_hit_marker_on_target(self, frame):
        target = frame.by_id(self.target_id)

        if target is None:
            return False

        markers = frame.overlapping(target, "hit_marker")

        new_markers = [
            hm
            for hm in markers
            if hm.id not in self.processed_hit_markers
        ]

        if not new_markers:
            return False

        for hm in new_markers:
            self.processed_hit_markers.add(hm.id)

        log.debug(f"Hit registered on target {self.target_id}")

        return True