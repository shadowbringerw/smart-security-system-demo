from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from .models import Detection, TrackObj


@dataclass
class _SimpleState:
    track_id: int
    bbox: Tuple[int, int, int, int]
    ttl: int


class _SimpleIoUTracker:
    def __init__(self, max_ttl: int = 12, iou_thresh: float = 0.35):
        self.max_ttl = max_ttl
        self.iou_thresh = iou_thresh
        self.next_id = 1
        self.states: Dict[int, _SimpleState] = {}

    @staticmethod
    def _iou(a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        if inter <= 0:
            return 0.0
        aa = max(1, (ax2 - ax1) * (ay2 - ay1))
        bb = max(1, (bx2 - bx1) * (by2 - by1))
        return inter / float(aa + bb - inter)

    def update(self, detections: List[Detection]) -> List[TrackObj]:
        assigned = set()
        outputs: List[TrackObj] = []

        for det in detections:
            best_id = None
            best_iou = 0.0
            for tid, st in self.states.items():
                iou = self._iou(st.bbox, det.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_id = tid

            if best_id is not None and best_iou >= self.iou_thresh:
                st = self.states[best_id]
                st.bbox = det.bbox
                st.ttl = self.max_ttl
                assigned.add(best_id)
                outputs.append(TrackObj(track_id=best_id, bbox=det.bbox, conf=det.conf))
            else:
                tid = self.next_id
                self.next_id += 1
                self.states[tid] = _SimpleState(track_id=tid, bbox=det.bbox, ttl=self.max_ttl)
                assigned.add(tid)
                outputs.append(TrackObj(track_id=tid, bbox=det.bbox, conf=det.conf))

        # decay unmatched tracks
        remove_ids = []
        for tid, st in self.states.items():
            if tid not in assigned:
                st.ttl -= 1
                if st.ttl <= 0:
                    remove_ids.append(tid)
        for tid in remove_ids:
            self.states.pop(tid, None)

        return outputs


class DeepSortTracker:
    def __init__(self):
        self._fallback = None
        self._deepsort = None
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort  # type: ignore

            self._deepsort = DeepSort(max_age=30, n_init=3)
        except Exception:
            self._fallback = _SimpleIoUTracker()

    def update(self, detections: List[Detection], frame) -> List[TrackObj]:
        if self._deepsort is None:
            return self._fallback.update(detections)

        dets = []
        for d in detections:
            x1, y1, x2, y2 = d.bbox
            w, h = max(1, x2 - x1), max(1, y2 - y1)
            dets.append(([x1, y1, w, h], d.conf, d.cls_name))

        tracks = self._deepsort.update_tracks(dets, frame=frame)
        out: List[TrackObj] = []
        for t in tracks:
            if not t.is_confirmed():
                continue
            ltrb = t.to_ltrb(orig=False)
            if ltrb is None:
                continue
            x1, y1, x2, y2 = map(int, ltrb)
            out.append(TrackObj(track_id=int(t.track_id), bbox=(x1, y1, x2, y2), conf=1.0))

        return out
