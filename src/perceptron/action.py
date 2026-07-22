import random
import time
import logging
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

    def find_window_partial(self, title):
        data = {"title": title, "results": []}
        win32gui.EnumWindows(enum_window_callback, data)
        return data["results"][0][0] if data["results"] else None

    def move_mouse(self, x, y, duration=0):
        if USE_POSTMESSAGE:
            self.move_postmessage(x, y, duration)
        else:
            self.move_pydirectinput(x, y, duration)

    def move_pydirectinput(self, x, y, duration):
        pydirectinput.moveTo(x, y, duration=duration, tween=pydirectinput.easeInOutQuad)

    def move_postmessage(self, x, y, duration):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return
        start_x, start_y = win32api.GetCursorPos()
        if duration <= 0:
            self.post_mouse_move(self.target_hwnd, x, y)
            return
        steps = max(1, int(duration * 100))
        for i in range(1, steps + 1):
            t = i / steps
            t = t * t * (3.0 - 2.0 * t)
            current_x, current_y = int(start_x + (x - start_x) * t), int(start_y + (y - start_y) * t)
            win32api.SetCursorPos((current_x, current_y))
            self.post_mouse_move(self.target_hwnd, current_x, current_y)
            time.sleep(duration / steps)

    def post_mouse_move(self, hwnd, screen_x, screen_y):
        client_x, client_y = win32gui.ScreenToClient(hwnd, (int(screen_x), int(screen_y)))
        lparam = win32api.MAKELONG(client_x & 0xFFFF, client_y & 0xFFFF)
        win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)

    def click(self, x, y):
        if USE_POSTMESSAGE:
            self.click_postmessage(x, y)
        else:
            self.click_pydirectinput()

    def click_pydirectinput(self):
        pydirectinput.click()

    def click_postmessage(self, x, y):
        if not self.target_hwnd:
            log.warning("Cannot use PostMessage: target_hwnd is not set.")
            return
        client_x, client_y = win32gui.ScreenToClient(self.target_hwnd, (int(x), int(y)))
        lparam = win32api.MAKELONG(client_x & 0xFFFF, client_y & 0xFFFF)
        win32gui.PostMessage(self.target_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(random.uniform(0.02, 0.06))
        win32gui.PostMessage(self.target_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

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

        if SMOOTH_MOUSE:
            travel_time = random.uniform(0.18, 0.38)
            log.debug(f"Moving to ({global_x}, {global_y}) over {travel_time:.2f}s")
            self.move_mouse(global_x, global_y, travel_time)
            time.sleep(random.uniform(0.04,0.09))
            self.click(global_x, global_y)

        else:
            log.debug(f"Instant click at ({global_x}, {global_y})")
            self.move_mouse(global_x, global_y, 0)
            self.click(global_x, global_y)

    def __init__(self, capture_area):
        self.offset_x = capture_area["left"]
        self.offset_y = capture_area["top"]
        self.width = capture_area["width"]
        self.height = capture_area["height"]
        self.target_hwnd = self.find_window_partial(WINDOW_NAME) if USE_POSTMESSAGE else None

        if USE_POSTMESSAGE and not self.target_hwnd:
            raise RuntimeError(f"Could not find window containing title: {WINDOW_NAME}")

def enum_window_callback(hwnd, matches):
    if not win32gui.IsWindowVisible(hwnd):
        return

    window_title = win32gui.GetWindowText(hwnd)

    if matches["title"].lower() in window_title.lower():
        matches["results"].append((hwnd, window_title))