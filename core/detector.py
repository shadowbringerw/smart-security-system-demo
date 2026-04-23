from __future__ import annotations

from typing import List

import cv2
import numpy as np

from .models import Detection


class YoloDetector:
    def __init__(self, model_name: str = "yolov8n.pt", device: str = "cpu"):
        self.backend = "bgsub"
        self.model = None
        try:
            from ultralytics import YOLO  # type: ignore
            self.model = YOLO(model_name)
            self.device = device
            self.backend = "yolo"
        except Exception:
            # Lightweight fallback to keep the end-to-end P0 pipeline runnable.
            self.bgsub = cv2.createBackgroundSubtractorMOG2(
                history=200, varThreshold=25, detectShadows=False
            )
            self.device = "cpu"

    def detect(self, frame, class_filter=("person",)) -> List[Detection]:
        if self.backend != "yolo":
            return self._detect_bgsub(frame, class_filter)

        results = self.model(frame, verbose=False, device=self.device)
        if not results:
            return []

        out: List[Detection] = []
        res = results[0]
        names = res.names
        if res.boxes is None:
            return out

        for b in res.boxes:
            cls_idx = int(b.cls.item())
            cls_name = names.get(cls_idx, str(cls_idx)) if isinstance(names, dict) else str(cls_idx)
            if class_filter and cls_name not in class_filter:
                continue
            conf = float(b.conf.item())
            x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
            out.append(Detection(bbox=(x1, y1, x2, y2), conf=conf, cls_name=cls_name))

        return out

    def _detect_bgsub(self, frame, class_filter=("person",)) -> List[Detection]:
        if class_filter and "person" not in class_filter:
            return []

        fg = self.bgsub.apply(frame)
        _, fg = cv2.threshold(fg, 180, 255, cv2.THRESH_BINARY)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        fg = cv2.morphologyEx(fg, cv2.MORPH_DILATE, np.ones((5, 5), np.uint8), iterations=1)
        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        out: List[Detection] = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < 900:
                continue
            x, y, w, h = cv2.boundingRect(c)
            if w < 20 or h < 40:
                continue
            conf = float(min(1.0, area / 12000.0))
            out.append(
                Detection(
                    bbox=(int(x), int(y), int(x + w), int(y + h)),
                    conf=conf,
                    cls_name="person",
                )
            )
        return out
