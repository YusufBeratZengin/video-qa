"""Validated, intentionally conservative editorial presets, not platform policy."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    name: str = "custom"
    width: int = 1080
    height: int = 1920
    aspect_ratio: float = 9 / 16
    aspect_tolerance: float = 0.01
    min_fps: float = 24.0
    max_fps: float = 60.0
    min_duration: float = 0.1
    max_duration: float = 60.0
    max_freeze: float = 1.5
    max_black: float = 0.5
    max_silence: float = 2.0
    silence_db: float = -50.0
    freeze_noise_db: float = -60.0
    black_pixel_threshold: float = 0.1
    black_picture_ratio: float = 0.98
    target_lufs: float = -14.0
    lufs_tolerance: float = 2.0
    max_peak_dbfs: float = -0.1
    require_audio: bool = True
    loudness_severity: str = "warn"

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if item.name in {"name", "loudness_severity", "require_audio"}:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"{item.name} must be a finite number")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a nonempty string")
        if type(self.require_audio) is not bool:
            raise ValueError("require_audio must be a boolean")
        if not isinstance(self.loudness_severity, str) or self.loudness_severity not in {
            "warn",
            "fail",
        }:
            raise ValueError("loudness_severity must be 'warn' or 'fail'")
        for key in ("width", "height"):
            if type(getattr(self, key)) is not int or getattr(self, key) <= 0:
                raise ValueError(f"{key} must be a positive integer")
        for key in ("aspect_ratio", "min_fps", "max_fps", "min_duration", "max_duration"):
            if getattr(self, key) <= 0:
                raise ValueError(f"{key} must be positive")
        for key in ("aspect_tolerance", "max_freeze", "max_black", "max_silence", "lufs_tolerance"):
            if getattr(self, key) < 0:
                raise ValueError(f"{key} must be nonnegative")
        if self.min_fps > self.max_fps or self.min_duration > self.max_duration:
            raise ValueError("Minimum bounds must not exceed maximum bounds")
        for key in ("silence_db", "freeze_noise_db", "max_peak_dbfs"):
            if getattr(self, key) > 0:
                raise ValueError(f"{key} must be <= 0 dB")
        for key in ("black_pixel_threshold", "black_picture_ratio"):
            if not 0 <= getattr(self, key) <= 1:
                raise ValueError(f"{key} must be between 0 and 1")
        if not -70 <= self.target_lufs <= -5:
            raise ValueError("target_lufs must be between -70 and -5")


BUILTINS = {
    "shorts": Profile(name="shorts"),
    "reels": Profile(name="reels", max_duration=90.0),
    "tiktok": Profile(name="tiktok", max_duration=180.0),
}


def load_profile(source: str) -> Profile:
    if source in BUILTINS:
        return BUILTINS[source]
    path = Path(source)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    elif path.suffix.lower() == ".toml":
        try:
            import tomllib
        except ImportError:  # Python 3.10
            import tomli as tomllib  # type: ignore[no-redef]
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    else:
        raise ValueError("Profile must be shorts, reels, tiktok, or a .json/.toml file")
    if not isinstance(data, dict):
        raise ValueError("Profile must be an object/table")
    base = data.pop("extends", "shorts")
    if not isinstance(base, str) or base not in BUILTINS:
        raise ValueError("extends must name a built-in profile")
    unknown = data.keys() - asdict(BUILTINS[base]).keys()
    if unknown:
        raise ValueError(f"Unknown profile keys: {', '.join(sorted(unknown))}")
    return replace(BUILTINS[base], **{"name": path.stem, **data})
