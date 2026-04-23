from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple


@dataclass
class AppConfig:
    model_name: str = "yolov8n.pt"
    device: str = "cpu"
    class_filter: Tuple[str, ...] = ("person",)

    run_speed_threshold: float = 35.0
    run_min_frames: int = 5

    gather_min_count: int = 3
    gather_max_avg_dist: float = 220.0
    gather_min_frames: int = 8

    fence_polygon: List[Tuple[int, int]] = field(
        default_factory=lambda: [(120, 100), (520, 100), (520, 380), (120, 380)]
    )

    db_path: Path = Path("data/alerts.db")
    snapshot_dir: Path = Path("data/snapshots")

    draw_trails_len: int = 20
