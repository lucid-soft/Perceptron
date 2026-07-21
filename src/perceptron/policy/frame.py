from collections import defaultdict
from dataclasses import dataclass, field
from ..detection import Detection

@dataclass(frozen=True, slots=True)
class FrameData:
    """Provides convenient indexed access to detections for a single frame."""

    detections: tuple[Detection, ...]
    center: tuple[int, int]

    _by_label: dict[str, tuple[Detection, ...]] = field(init=False, repr=False)
    _by_id: dict[int, Detection] = field(init=False, repr=False)

    def __post_init__(self):
        by_label = defaultdict(list)
        by_id = {}

        for det in self.detections:
            by_label[det.label].append(det)
            by_id[det.id] = det

        immutable_by_label = {
            label: tuple(detections)
            for label, detections in by_label.items()
        }

        object.__setattr__(self, "_by_label", immutable_by_label)
        object.__setattr__(self, "_by_id", by_id)

    def by_label(self, label: str) -> tuple[Detection, ...]:
        return self._by_label.get(label, ())

    def by_id(self, track_id: int) -> Detection | None:
        return self._by_id.get(track_id)

    def closest(
            self,
            label: str,
            point: tuple[int, int] | None = None,
    ) -> Detection | None:
        """
        Returns the closest detection of the requested label.

        If point is omitted, the center of the capture area is used.
        """
        detections = self.by_label(label)

        if not detections:
            return None

        if point is None:
            point = self.center

        px, py = point

        return min(
            detections,
            key=lambda d: (
                    (d.center[0] - px) ** 2
                    + (d.center[1] - py) ** 2
            ),
        )

    def overlapping(
            self,
            target: Detection | None,
            label: str | None = None,
    ) -> list[Detection]:
        """
        Returns all detections whose center lies inside the target's
        bounding box.
        """
        if target is None:
            return []

        gx1, gy1, gx2, gy2 = target.box

        detections = (
            self.detections
            if label is None
            else self.by_label(label)
        )

        return [
            det
            for det in detections
            if gx1 <= det.center[0] <= gx2
               and gy1 <= det.center[1] <= gy2
        ]

    def first_overlapping(
            self,
            target: Detection | None,
            label: str | None = None,
    ) -> Detection | None:
        overlaps = self.overlapping(target, label)
        return overlaps[0] if overlaps else None

    def contains(
            self,
            target: Detection | None,
            label: str | None = None,
    ) -> bool:
        return self.first_overlapping(target, label) is not None