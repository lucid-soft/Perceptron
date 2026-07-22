import random
import time
import logging
import threading
import queue
import cv2
import numpy as np
import pydirectinput
import win32gui
import win32con
import win32api

from src.perceptron.config import SMOOTH_MOUSE, USE_POSTMESSAGE, WINDOW_NAME

pydirectinput.PAUSE = 0.05
log = logging.getLogger(__name__)

class ActionLayer:
    """Handles physical hardware interactions with humanization and safety bounds."""

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
            self._key_up(key)

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

            with self.mouse_lock:
                if self.pending_mouse_action is not None:
                    action = self.pending_mouse_action
                    self.pending_mouse_action = None

                    if action is not None:
                        try:
                            self._execute_mouse_action(action)
                        except Exception:

                            log.exception("Error executing mouse action.")

    def _execute_action(self, action):
        action_type = action["type"]
        data = action["data"]

        if action_type == "key_press":
            self._key_press(data["key"])

        elif action_type == "key_down":
            self._key_down(data["key"])

        elif action_type == "key_up":
            self._key_up(data["key"])

        elif action_type == "sleep":
            time.sleep(data["duration"])

    def _execute_mouse_action(self, action):
        x = action["x"]
        y = action["y"]

        travel_time = random.uniform(0.18, 0.38) if SMOOTH_MOUSE else 0
        log.debug(f"Moving to ({x}, {y}) over {travel_time:.2f}s")

        if not self._move_mouse(x, y, travel_time):
            log.debug("Mouse movement cancelled by newer target.")
            return

        # Check again before clicking.
        with self.mouse_lock:
            if self.pending_mouse_action is not None:
                log.debug("Mouse action replaced before click.")
                return

        self._click(x, y)

    def _interruptible_sleep(self, duration):
        end_time = time.monotonic() + duration

        while time.monotonic() < end_time:
            with self.mouse_lock:
                if self.pending_mouse_action is not None:
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
    # Keyboard action
    # ==================================================

    def _submit_action(self, action_type, **kwargs):
        self.action_queue.put({
            "type": action_type,
            "data": kwargs
        })

    def _key_press(self, key):
        if USE_POSTMESSAGE:
            self._key_press_postmessage(key)
        else:
            pydirectinput.press(key)

    def _key_down(self, key):
        if USE_POSTMESSAGE:
            self._key_down_postmessage(key)
        else:
            pydirectinput.keyDown(key)

    def _key_up(self, key):
        if USE_POSTMESSAGE:
            self._key_up_postmessage(key)
        else:
            pydirectinput.keyUp(key)

    def _action_sleep(self, duration):
        self._submit_action("sleep", duration=duration)

    def _make_key_lparam(self, vk_code, key_up=False):
        scan_code = win32api.MapVirtualKey(vk_code, 0)

        lparam = 1 | (scan_code << 16)

        if key_up:
            lparam |= (1 << 30)  # Previous key state
            lparam |= (1 << 31)  # Transition state

        return lparam


    def _key_press_postmessage(self, key):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return

        vk_code = get_virtual_key_code(key)

        if vk_code is None:
            log.warning(f"Unsupported key: {key}")
            return

        key_down_lparam = self._make_key_lparam(vk_code, key_up=False)
        key_up_lparam = self._make_key_lparam(vk_code, key_up=True)

        win32gui.PostMessage(
            self.target_hwnd,
            win32con.WM_KEYDOWN,
            vk_code,
            key_down_lparam
        )

        time.sleep(random.uniform(0.02, 0.07))

        win32gui.PostMessage(
            self.target_hwnd,
            win32con.WM_KEYUP,
            vk_code,
            key_up_lparam
        )


    def _key_down_postmessage(self, key):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return

        vk_code = get_virtual_key_code(key)

        if vk_code is None:
            log.warning(f"Unsupported key: {key}")
            return

        lparam = self._make_key_lparam(vk_code, key_up=False)

        win32gui.PostMessage(
            self.target_hwnd,
            win32con.WM_KEYDOWN,
            vk_code,
            lparam
        )


    def _key_up_postmessage(self, key):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return

        vk_code = get_virtual_key_code(key)

        if vk_code is None:
            log.warning(f"Unsupported key: {key}")
            return

        lparam = self._make_key_lparam(vk_code, key_up=True)

        win32gui.PostMessage(
            self.target_hwnd,
            win32con.WM_KEYUP,
            vk_code,
            lparam
        )

    # ==================================================
    # Mouse action
    # ==================================================

    def _submit_mouse_action(self, x, y):
        with self.mouse_lock:
            self.pending_mouse_action = {
                "x": x,
                "y": y
            }

    def _move_mouse(self, x, y, duration=0):
        if USE_POSTMESSAGE:
            return self._move_postmessage(x, y, duration)
        else:
            return self._move_pydirectinput(x, y, duration)

    def _move_pydirectinput(self, x, y, duration):
        if duration <= 0:
            pydirectinput.moveTo(x, y, duration=0)
            return True

        start_x, start_y = win32api.GetCursorPos()
        steps = max(1, int(duration * 100))

        for i in range(1, steps + 1):
            # Check for a newer target before each movement step.
            with self.mouse_lock:
                if self.pending_mouse_action is not None:
                    return False

            t = i / steps
            t = t * t * (3.0 - 2.0 * t)

            current_x = int(start_x + (x - start_x) * t)
            current_y = int(start_y + (y - start_y) * t)

            pydirectinput.moveTo(current_x, current_y, duration=0)

            time.sleep(duration / steps)

        return True

    def _move_postmessage(self, x, y, duration):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return False

        start_x, start_y = win32api.GetCursorPos()

        if duration <= 0:
            self._post_mouse_move(self.target_hwnd, x, y)
            win32api.SetCursorPos((x, y))
            return True

        steps = max(1, int(duration * 100))

        for i in range(1, steps + 1):
            # Check for a newer target before each movement step.
            with self.mouse_lock:
                if self.pending_mouse_action is not None:
                    return False

            t = i / steps
            t = t * t * (3.0 - 2.0 * t)

            current_x, current_y = int(start_x + (x - start_x) * t), int(start_y + (y - start_y) * t)

            self._post_mouse_move(self.target_hwnd, current_x, current_y)
            win32api.SetCursorPos((current_x, current_y))

            time.sleep(duration / steps)

        return True

    def _post_mouse_move(self, hwnd, screen_x, screen_y):
        client_x, client_y = win32gui.ScreenToClient(hwnd, (int(screen_x), int(screen_y)))
        lparam = win32api.MAKELONG(client_x & 0xFFFF, client_y & 0xFFFF)
        win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)

    def _click(self, x, y):
        if USE_POSTMESSAGE:
            self._click_postmessage(x, y)
        else:
            self._click_pydirectinput()

    def _click_pydirectinput(self):
        pydirectinput.click()

    def _click_postmessage(self, x, y):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return
        client_x, client_y = win32gui.ScreenToClient(self.target_hwnd, (int(x), int(y)))
        lparam = win32api.MAKELONG(client_x & 0xFFFF, client_y & 0xFFFF)
        win32gui.PostMessage(self.target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(random.uniform(0.02, 0.06))
        win32gui.PostMessage(self.target_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    # ==================================================
    # Wrapper / Helper methods
    # ==================================================

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
            "!": "1",
            "@": "2",
            "#": "3",
            "$": "4",
            "%": "5",
            "^": "6",
            "&": "7",
            "*": "8",
            "(": "9",
            ")": "0",
            "_": "-",
            "+": "=",
            "{": "[",
            "}": "]",
            "|": "\\",
            ":": ";",
            '"': "'",
            "<": ",",
            ">": ".",
            "?": "/",
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

    def humanized_click(self, target):
        """Select a weighted random point inside an object's segmentation mask."""

        local_x = None
        local_y = None

        # Segmentation mask click selection
        mask_xy = target.mask_xy

        if mask_xy is not None and len(mask_xy) > 2:

            polygon = np.asarray(mask_xy, dtype=np.int32)

            # Bounding rectangle around the polygon
            x, y, w, h = cv2.boundingRect(polygon)

            # Convert polygon into local coordinates
            local_poly = polygon - [x, y]

            # Rasterize polygon into a binary mask
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(mask, [local_poly], 255)

            # Compute distance from every interior pixel to the nearest edge
            dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)

            # Every valid pixel inside the mask
            valid_y, valid_x = np.where(dist > 1.0)

            if len(valid_x) == 0:
                valid_y, valid_x = np.where(mask == 255)

            if len(valid_x) > 0:

                # Distance values become sampling weights
                weights = dist[valid_y, valid_x].astype(np.float64)

                # Strongly bias toward the interior
                weights **= 2

                total = weights.sum()

                if total > 0:
                    weights /= total
                    idx = np.random.choice(len(valid_x), p=weights)
                else:
                    idx = random.randrange(len(valid_x))

                local_x = int(x + valid_x[idx])
                local_y = int(y + valid_y[idx])

            else:
                log.debug("Empty mask. Falling back to center.")

                local_x = x + w // 2
                local_y = y + h // 2

        # --------------------------------------------------
        # Bounding-box fallback
        # --------------------------------------------------
        else:
            x1, y1, x2, y2 = target.box

            padding_w = (x2 - x1) * 0.25
            padding_h = (y2 - y1) * 0.25

            local_x = int(random.uniform(x1 + padding_w, x2 - padding_w))
            local_y = int(random.uniform(y1 + padding_h, y2 - padding_h))

        # --------------------------------------------------
        # Safety bounds
        # --------------------------------------------------
        if not (0 <= local_x < self.width and 0 <= local_y < self.height):
            log.debug(f"REJECTED! Target ({local_x}, {local_y}) out of bounds.")
            return

        global_x = self.offset_x + local_x
        global_y = self.offset_y + local_y

        click_type = "smooth" if SMOOTH_MOUSE else "instant"
        log.debug(f"Submitting {click_type} click at ({global_x}, {global_y})")

        self._submit_mouse_action(global_x, global_y)

    def __init__(self, capture_area):
        self.offset_x = capture_area["left"]
        self.offset_y = capture_area["top"]
        self.width = capture_area["width"]
        self.height = capture_area["height"]
        self.target_hwnd = find_window_partial(WINDOW_NAME) if USE_POSTMESSAGE else None

        if USE_POSTMESSAGE and not self.target_hwnd:
            raise RuntimeError(f"Could not find window containing title: {WINDOW_NAME}")

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

def find_window_partial(title):
    data = {"title": title, "results": []}
    win32gui.EnumWindows(enum_window_callback, data)
    return data["results"][0][0] if data["results"] else None

def enum_window_callback(hwnd, matches):
    if not win32gui.IsWindowVisible(hwnd):
        return

    window_title = win32gui.GetWindowText(hwnd)

    if matches["title"].lower() in window_title.lower():
        matches["results"].append((hwnd, window_title))

def get_virtual_key_code(key):
    key = key.lower()

    key_map = {
        "enter": win32con.VK_RETURN,
        "return": win32con.VK_RETURN,
        "escape": win32con.VK_ESCAPE,
        "esc": win32con.VK_ESCAPE,
        "space": win32con.VK_SPACE,
        "tab": win32con.VK_TAB,
        "backspace": win32con.VK_BACK,
        "shift": win32con.VK_SHIFT,
        "ctrl": win32con.VK_CONTROL,
        "control": win32con.VK_CONTROL,
        "alt": win32con.VK_MENU,
        "left": win32con.VK_LEFT,
        "right": win32con.VK_RIGHT,
        "up": win32con.VK_UP,
        "down": win32con.VK_DOWN,
    }

    if key in key_map:
        return key_map[key]

    if len(key) == 1:
        return ord(key.upper())

    if key.startswith("f") and key[1:].isdigit():
        function_number = int(key[1:])

        if 1 <= function_number <= 24:
            return win32con.VK_F1 + function_number - 1

    return None