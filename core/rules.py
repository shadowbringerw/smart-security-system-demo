from __future__ import annotations

from collections import defaultdict, deque
from math import sqrt
from typing import Deque, Dict, List, Tuple

import numpy as np

from .models import AlertEvent, TrackObj


class BehaviorRules:
    def __init__(
        self,
        run_speed_threshold: float,
        run_min_frames: int,
        gather_min_count: int,
        gather_max_avg_dist: float,
        gather_min_frames: int,
    ):
        self.run_speed_threshold = run_speed_threshold
        self.run_min_frames = run_min_frames
        self.gather_min_count = gather_min_count
        self.gather_max_avg_dist = gather_max_avg_dist
        self.gather_min_frames = gather_min_frames

        self.history: Dict[int, Deque[Tuple[int, int]]] = defaultdict(lambda: deque(maxlen=30))
        self.run_streak: Dict[int, int] = defaultdict(int)
        self.gather_streak = 0

        self._cooldown: Dict[Tuple[str, int], int] = defaultdict(int)

    @staticmethod
    def _center(bbox):
        x1, y1, x2, y2 = bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    @staticmethod
    def point_in_polygon(pt: Tuple[int, int], polygon: List[Tuple[int, int]]) -> bool:
        # ray casting
        x, y = pt
        inside = False
        n = len(polygon)
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            cond = ((y1 > y) != (y2 > y)) and (
                x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
            )
            if cond:
                inside = not inside
        return inside

    def _on_cooldown(self, key: Tuple[str, int], frame_idx: int, gap=30) -> bool:
        last = self._cooldown.get(key, -10_000)
        if frame_idx - last < gap:
            return True
        self._cooldown[key] = frame_idx
        return False

    def evaluate(
        self,
        tracks: List[TrackObj],
        frame_idx: int,
        ts_ms: int,
        fence_polygon: List[Tuple[int, int]],
        fps: float,
    ) -> List[AlertEvent]:
        alerts: List[AlertEvent] = []

        # Intrusion and running by track
        centers = []
        for t in tracks:
            c = self._center(t.bbox)
            centers.append((t.track_id, c))
            self.history[t.track_id].append(c)

            # Intrusion
            if fence_polygon and self.point_in_polygon(c, fence_polygon):
                key = ("intrusion", t.track_id)
                if not self._on_cooldown(key, frame_idx):
                    alerts.append(
                        AlertEvent(
                            event_type="intrusion",
                            track_id=t.track_id,
                            score=0.95,
                            message="Track entered electronic fence area",
                            frame_index=frame_idx,
                            ts_ms=ts_ms,
                        )
                    )

            # Running
            hist = self.history[t.track_id]
            if len(hist) >= 2:
                (x1, y1), (x2, y2) = hist[-2], hist[-1]
                speed_px_s = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * max(fps, 1.0)
                if speed_px_s >= self.run_speed_threshold:
                    self.run_streak[t.track_id] += 1
                else:
                    self.run_streak[t.track_id] = 0

                if self.run_streak[t.track_id] >= self.run_min_frames:
                    key = ("running", t.track_id)
                    if not self._on_cooldown(key, frame_idx):
                        alerts.append(
                            AlertEvent(
                                event_type="running",
                                track_id=t.track_id,
                                score=min(1.0, speed_px_s / (self.run_speed_threshold + 1e-6)),
                                message=f"Track running detected speed={speed_px_s:.1f}px/s",
                                frame_index=frame_idx,
                                ts_ms=ts_ms,
                            )
                        )

        # Gathering (global)
        pts = [c for _, c in centers]
        if len(pts) >= self.gather_min_count:
            dists = []
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    d = sqrt((pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2)
                    dists.append(d)
            avg_dist = float(np.mean(dists)) if dists else 10_000.0
            if avg_dist <= self.gather_max_avg_dist:
                self.gather_streak += 1
            else:
                self.gather_streak = 0

            if self.gather_streak >= self.gather_min_frames:
                key = ("gathering", -1)
                if not self._on_cooldown(key, frame_idx):
                    alerts.append(
                        AlertEvent(
                            event_type="gathering",
                            track_id=-1,
                            score=min(1.0, len(pts) / (self.gather_min_count + 1e-6)),
                            message=f"Possible crowd gathering count={len(pts)} avg_dist={avg_dist:.1f}",
                            frame_index=frame_idx,
                            ts_ms=ts_ms,
                        )
                    )
        else:
            self.gather_streak = 0

        return alerts
