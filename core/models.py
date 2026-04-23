from dataclasses import dataclass
from typing import Tuple


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]
    conf: float
    cls_name: str


@dataclass
class TrackObj:
    track_id: int
    bbox: Tuple[int, int, int, int]
    conf: float


@dataclass
class AlertEvent:
    event_type: str
    track_id: int
    score: float
    message: str
    frame_index: int
    ts_ms: int
