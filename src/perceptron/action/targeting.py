import cv2
import numpy as np
import random
import logging

log = logging.getLogger(__name__)

def calculate_humanized_coordinates(target, width, height, offset_x, offset_y):
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
    if not (0 <= local_x < width and 0 <= local_y < height):
        log.debug(f"REJECTED! Target ({local_x}, {local_y}) out of bounds.")
        return None

    global_x = offset_x + local_x
    global_y = offset_y + local_y

    return global_x, global_y