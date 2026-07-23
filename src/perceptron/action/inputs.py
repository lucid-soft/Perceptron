import time
import random
import logging
import pydirectinput
import win32gui
import win32con
import win32api

from src.perceptron.config import USE_POSTMESSAGE
from src.perceptron.action.utils import get_virtual_key_code, make_key_lparam

pydirectinput.PAUSE = 0.05
log = logging.getLogger(__name__)

class KeyboardBackend:
    def __init__(self, target_hwnd):
        self.target_hwnd = target_hwnd

    def press(self, key):
        if USE_POSTMESSAGE:
            self._key_press_postmessage(key)
        else:
            pydirectinput.press(key)

    def down(self, key):
        if USE_POSTMESSAGE:
            self._key_down_postmessage(key)
        else:
            pydirectinput.keyDown(key)

    def up(self, key):
        if USE_POSTMESSAGE:
            self._key_up_postmessage(key)
        else:
            pydirectinput.keyUp(key)

    def _key_press_postmessage(self, key):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return

        vk_code = get_virtual_key_code(key)

        if vk_code is None:
            log.warning(f"Unsupported key: {key}")
            return

        key_down_lparam = make_key_lparam(vk_code, key_up=False)
        key_up_lparam = make_key_lparam(vk_code, key_up=True)

        win32gui.PostMessage(self.target_hwnd, win32con.WM_KEYDOWN, vk_code, key_down_lparam)
        time.sleep(random.uniform(0.02, 0.07))
        win32gui.PostMessage(self.target_hwnd, win32con.WM_KEYUP, vk_code, key_up_lparam)

    def _key_down_postmessage(self, key):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return

        vk_code = get_virtual_key_code(key)

        if vk_code is None:
            log.warning(f"Unsupported key: {key}")
            return

        lparam = make_key_lparam(vk_code, key_up=False)
        win32gui.PostMessage(self.target_hwnd, win32con.WM_KEYDOWN, vk_code, lparam)

    def _key_up_postmessage(self, key):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return

        vk_code = get_virtual_key_code(key)

        if vk_code is None:
            log.warning(f"Unsupported key: {key}")
            return

        lparam = make_key_lparam(vk_code, key_up=True)
        win32gui.PostMessage(self.target_hwnd, win32con.WM_KEYUP, vk_code, lparam)


class MouseBackend:
    def __init__(self, target_hwnd):
        self.target_hwnd = target_hwnd

    def move(self, x, y, duration=0, cancel_check=lambda: False):
        if USE_POSTMESSAGE:
            return self._move_postmessage(x, y, duration, cancel_check)
        else:
            return self._move_pydirectinput(x, y, duration, cancel_check)

    def click(self, x, y):
        if USE_POSTMESSAGE:
            self._click_postmessage(x, y)
        else:
            self._click_pydirectinput()

    def _move_pydirectinput(self, x, y, duration, cancel_check):
        if duration <= 0:
            pydirectinput.moveTo(x, y, duration=0)
            return True

        start_x, start_y = win32api.GetCursorPos()
        steps = max(1, int(duration * 100))

        for i in range(1, steps + 1):
            # Check for a newer target before each movement step.
            if cancel_check():
                return False

            t = i / steps
            t = t * t * (3.0 - 2.0 * t)

            current_x = int(start_x + (x - start_x) * t)
            current_y = int(start_y + (y - start_y) * t)

            pydirectinput.moveTo(current_x, current_y, duration=0)

            time.sleep(duration / steps)

        return True

    def _move_postmessage(self, x, y, duration, cancel_check):
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
            if cancel_check():
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