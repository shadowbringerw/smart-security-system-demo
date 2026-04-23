from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Tuple

import cv2

from config import AppConfig
from .detector import YoloDetector
from .models import Detection, TrackObj
from .rules import BehaviorRules
from .storage import AlertStore
from .tracker import DeepSortTracker


class VideoPipeline:
    def __init__(self, cfg: AppConfig, source: str):
        self.cfg = cfg
        self.source = source

        self.detector = YoloDetector(cfg.model_name, cfg.device)
        self.tracker = DeepSortTracker()
        self.rules = BehaviorRules(
            run_speed_threshold=cfg.run_speed_threshold,
            run_min_frames=cfg.run_min_frames,
            gather_min_count=cfg.gather_min_count,
            gather_max_avg_dist=cfg.gather_max_avg_dist,
            gather_min_frames=cfg.gather_min_frames,
        )
        self.store = AlertStore(cfg.db_path)

        self._latest_jpeg = None
        self._lock = threading.Lock()
        self._thread = None
        self._stop = threading.Event()

        self.frame_idx = 0
        self.fps = 0.0
        self.last_proc_ms = 0.0
        self.last_alert_ts_ms = 0
        self.current_track_count = 0
        self.last_frame_shape = None
        self.started_at = time.time()
        self.track_points: Dict[int, Deque[Tuple[int, int]]] = defaultdict(lambda: deque(maxlen=cfg.draw_trails_len))

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def set_fence_polygon(self, polygon: List[Tuple[int, int]]):
        self.cfg.fence_polygon = polygon

    def set_rules(self, payload: dict):
        if "run_speed_threshold" in payload:
            self.rules.run_speed_threshold = float(payload["run_speed_threshold"])
        if "run_min_frames" in payload:
            self.rules.run_min_frames = int(payload["run_min_frames"])
        if "gather_min_count" in payload:
            self.rules.gather_min_count = int(payload["gather_min_count"])
        if "gather_max_avg_dist" in payload:
            self.rules.gather_max_avg_dist = float(payload["gather_max_avg_dist"])
        if "gather_min_frames" in payload:
            self.rules.gather_min_frames = int(payload["gather_min_frames"])

    def _draw(self, frame, tracks: List[TrackObj], alerts):
        # fence
        poly = self.cfg.fence_polygon
        if poly and len(poly) >= 3:
            for i in range(len(poly)):
                p1 = poly[i]
                p2 = poly[(i + 1) % len(poly)]
                cv2.line(frame, p1, p2, (0, 255, 255), 2)

        for t in tracks:
            x1, y1, x2, y2 = t.bbox
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            self.track_points[t.track_id].append((cx, cy))
            cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 220, 80), 2)
            cv2.putText(
                frame,
                f"ID {t.track_id}",
                (x1, max(20, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (80, 220, 80),
                2,
            )
            pts = list(self.track_points[t.track_id])
            for i in range(1, len(pts)):
                cv2.line(frame, pts[i - 1], pts[i], (120, 200, 255), 2)

        y = 25
        for a in alerts[:3]:
            cv2.putText(
                frame,
                f"ALERT {a.event_type}: {a.message}",
                (8, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 255),
                2,
            )
            y += 24

        cv2.putText(
            frame,
            f"FPS {self.fps:.1f} | proc {self.last_proc_ms:.1f} ms | tracks {len(tracks)}",
            (8, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 0),
            2,
        )

        return frame

    def _loop(self):
        cap = cv2.VideoCapture(0 if self.source == "0" else self.source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open source: {self.source}")

        prev = time.time()
        while not self._stop.is_set():
            ok, frame = cap.read()
            if not ok:
                break

            t0 = time.time()
            self.frame_idx += 1
            ts_ms = int(t0 * 1000)

            detections = self.detector.detect(frame, class_filter=self.cfg.class_filter)
            tracks = self.tracker.update(detections, frame)
            self.current_track_count = len(tracks)
            self.last_frame_shape = frame.shape[:2]
            alerts = self.rules.evaluate(
                tracks=tracks,
                frame_idx=self.frame_idx,
                ts_ms=ts_ms,
                fence_polygon=self.cfg.fence_polygon,
                fps=max(self.fps, 1.0),
            )
            if alerts:
                self.last_alert_ts_ms = ts_ms
            self.store.add_events(alerts)

            frame = self._draw(frame, tracks, alerts)
            ok, jpg = cv2.imencode(".jpg", frame)
            if ok:
                with self._lock:
                    self._latest_jpeg = jpg.tobytes()

            now = time.time()
            dt = now - prev
            prev = now
            self.fps = 1.0 / dt if dt > 0 else 0.0
            self.last_proc_ms = (now - t0) * 1000

        cap.release()

    def get_frame_jpeg(self):
        with self._lock:
            return self._latest_jpeg

    def get_stats(self):
        height, width = self.last_frame_shape or (0, 0)
        return {
            "frame_index": self.frame_idx,
            "fps": round(self.fps, 2),
            "proc_ms": round(self.last_proc_ms, 2),
            "source": "camera:0" if self.source == "0" else self.source,
            "uptime_s": int(max(0, time.time() - self.started_at)),
            "track_count": self.current_track_count,
            "detector_backend": self.detector.backend,
            "tracker_backend": "deepsort" if self.tracker._deepsort is not None else "iou-fallback",
            "frame_width": width,
            "frame_height": height,
            "last_alert_ts_ms": self.last_alert_ts_ms,
            "fence_polygon": self.cfg.fence_polygon,
            "rules": {
                "run_speed_threshold": self.rules.run_speed_threshold,
                "run_min_frames": self.rules.run_min_frames,
                "gather_min_count": self.rules.gather_min_count,
                "gather_max_avg_dist": self.rules.gather_max_avg_dist,
                "gather_min_frames": self.rules.gather_min_frames,
            },
        }
