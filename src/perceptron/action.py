import random
import time
import logging
import cv2
import numpy as np
import pydirectinput

from src.perceptron.config import SMOOTH_MOUSE

pydirectinput.PAUSE = 0.05
log = logging.getLogger(__name__)

class ActionLayer:
    """Handles physical hardware interactions with humanization and safety bounds."""

    def __init__(self, capture_area):
        self.offset_x = capture_area["left"]
        self.offset_y = capture_area["top"]
        self.width = capture_area["width"]
        self.height = capture_area["height"]

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

            pydirectinput.moveTo(
                global_x,
                global_y,
                duration=travel_time,
                tween=pydirectinput.easeInOutQuad,
            )

            time.sleep(random.uniform(0.04, 0.09))
            pydirectinput.click()

        else:
            log.debug(f"Instant click at ({global_x}, {global_y})")
            pydirectinput.click(global_x, global_y)