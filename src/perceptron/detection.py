from dataclasses import dataclass
from typing import Optional

import numpy as np

@dataclass(frozen=True, slots=True)
class Detection:
    """
    Represents a single tracked object detected by the perception layer.

    The center is the representative point of the detection. It is currently
    the center of the bounding box, but may later become the segmentation
    centroid without affecting the rest of the application.
    """

    id: int
    label: str
    center: tuple[int, int]
    box: tuple[int, int, int, int]
    mask_xy: Optional[np.ndarray]