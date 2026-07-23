import random
import time
import logging
import threading
import queue

from src.perceptron.config import SMOOTH_MOUSE, USE_POSTMESSAGE, WINDOW_NAME
from src.perceptron.action.utils import find_window_partial
from src.perceptron.action.inputs import KeyboardBackend, MouseBackend
from src.perceptron.action.targeting import calculate_humanized_coordinates

log = logging.getLogger(__name__)

class ActionLayer:
    """Handles physical hardware interactions with humanization and safety bounds."""

    def __init__(self, capture_area):
        self.offset_x = capture_area["left"]
        self.offset_y = capture_area["top"]
        self.width = capture_area["width"]
        self.height = capture_area["height"]

        self.target_hwnd = find_window_partial(WINDOW_NAME) if USE_POSTMESSAGE else None

        if USE_POSTMESSAGE and not self.target_hwnd:
            raise RuntimeError(f"Could not find window containing title: {WINDOW_NAME}")

        self.keyboard = KeyboardBackend(self.target_hwnd)
        self.mouse = MouseBackend(self.target_hwnd)

        # Ordered actions such as keyboard input.
        self.action_queue = queue.Queue()

        # Latest mouse action only.
        self.pending_mouse_action = None
        self.mouse_lock = threading.Lock()

        self.held_keys = {}
        self.key_lock = threading.Lock()

        self.running = True

        self.action_thread = threading.Thread(
            target=self._action_worker,
            name="ActionWorker",
            daemon=True
        )

        self.action_thread.start()

    # ==================================================
    # Actions
    # ==================================================

    def _check_held_keys(self):
        now = time.monotonic()
        keys_to_release = []

        with self.key_lock:
            for key, data in self.held_keys.items():
                if now - data["pressed_at"] >= data["hold_time"]:
                    keys_to_release.append(key)

            for key in keys_to_release:
                del self.held_keys[key]

        for key in keys_to_release:
            self.keyboard.up(key)

    def _action_worker(self):
        while self.running:
            action = None
            self._check_held_keys()

            # Keyboard and other later actions take priority.
            try:
                action = self.action_queue.get(timeout=0.01)
            except queue.Empty:
                pass

            if action is not None:
                try:
                    self._execute_action(action)
                except Exception:
                    log.exception("Error executing action.")
                finally:
                    self.action_queue.task_done()

            mouse_action = None
            with self.mouse_lock:
                if self.pending_mouse_action is not None:
                    mouse_action = self.pending_mouse_action
                    self.pending_mouse_action = None

            if mouse_action is not None:
                try:
                    self._execute_mouse_action(mouse_action)
                except Exception:
                    log.exception("Error executing mouse action.")

    def _execute_action(self, action):
        action_type = action["type"]
        data = action["data"]

        if action_type == "key_press":
            self.keyboard.press(data["key"])

        elif action_type == "key_down":
            self.keyboard.down(data["key"])

        elif action_type == "key_up":
            self.keyboard.up(data["key"])

        elif action_type == "sleep":
            time.sleep(data["duration"])

    def _is_mouse_cancelled(self):
        with self.mouse_lock:
            return self.pending_mouse_action is not None

    def _execute_mouse_action(self, action):
        x = action["x"]
        y = action["y"]

        travel_time = random.uniform(0.18, 0.38) if SMOOTH_MOUSE else 0
        log.debug(f"Moving to ({x}, {y}) over {travel_time:.2f}s")

        # Pass the threading lock check as a callback to preserve clean separation
        if not self.mouse.move(x, y, travel_time, self._is_mouse_cancelled):
            log.debug("Mouse movement cancelled by newer target.")
            return

        # Check again before clicking.
        if self._is_mouse_cancelled():
            log.debug("Mouse action replaced before click.")
            return

        self.mouse.click(x, y)

    def _interruptible_sleep(self, duration):
        end_time = time.monotonic() + duration

        while time.monotonic() < end_time:
            if self._is_mouse_cancelled():
                return True

            time.sleep(0.005)

        return False

    def stop(self):
        with self.key_lock:
            held_keys = list(self.held_keys)
            self.held_keys.clear()

        for key in held_keys:
            self._submit_action("key_up", key=key)

        self.running = False

        with self.mouse_lock:
            self.pending_mouse_action = None

        if self.action_thread.is_alive() and threading.current_thread() is not self.action_thread:
            self.action_thread.join(timeout=1.0)

    # ==================================================
    # Keyboard action wrappers
    # ==================================================

    def _submit_action(self, action_type, **kwargs):
        self.action_queue.put({
            "type": action_type,
            "data": kwargs
        })

    def hold_key(self, key, duration):
        with self.key_lock:
            if key in self.held_keys:
                return

            self.held_keys[key] = {
                "pressed_at": time.monotonic(),
                "hold_time": duration
            }

        self._submit_action("key_down", key=key)

    def release_key(self, key):
        with self.key_lock:
            if key not in self.held_keys:
                return

            del self.held_keys[key]

        self._submit_action("key_up", key=key)

    def press_key(self, key):
        self._submit_action("key_press", key=key)

    def type_message(self, message):
        shift_map = {
            "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6",
            "&": "7", "*": "8", "(": "9", ")": "0", "_": "-", "+": "=",
            "{": "[", "}": "]", "|": "\\", ":": ";", '"': "'", "<": ",",
            ">": ".", "?": "/",
        }

        for character in message:
            if character == " ":
                self._submit_action("key_press", key="space")
            elif character == "\n":
                self._submit_action("key_press", key="enter")
            elif character.isupper():
                self._submit_action("key_down", key="shift")
                self._submit_action("key_press", key=character.lower())
                self._submit_action("key_up", key="shift")
            elif character in shift_map:
                self._submit_action("key_down", key="shift")
                self._submit_action("key_press", key=shift_map[character])
                self._submit_action("key_up", key="shift")
            else:
                self._submit_action("key_press", key=character)

    # ==================================================
    # Mouse action wrappers
    # ==================================================

    def _submit_mouse_action(self, x, y):
        with self.mouse_lock:
            self.pending_mouse_action = {
                "x": x,
                "y": y
            }

    def humanized_click(self, target):
        coords = calculate_humanized_coordinates(
            target, self.width, self.height, self.offset_x, self.offset_y
        )

        if coords:
            global_x, global_y = coords
            click_type = "smooth" if SMOOTH_MOUSE else "instant"
            log.debug(f"Submitting {click_type} click at ({global_x}, {global_y})")
            self._submit_mouse_action(global_x, global_y)