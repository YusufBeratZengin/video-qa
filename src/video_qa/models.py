"""Small, serializable data structures shared by parsers and rules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Interval:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(frozen=True)
class MediaInfo:
    width: int
    height: int
    fps: float
    duration: float
    has_audio: bool
    video_duration: float
    audio_duration: float | None = None
    sample_aspect_ratio: float = 1.0
    rotation: int = 0
    video_streams: int = 1
    audio_streams: int = 0

    @property
    def display_aspect_ratio(self) -> float:
        ratio = self.width * self.sample_aspect_ratio / self.height
        return 1 / ratio if self.rotation % 180 else ratio


@dataclass(frozen=True)
class Measurements:
    freezes: list[Interval] = field(default_factory=list)
    black: list[Interval] = field(default_factory=list)
    silence: list[Interval] = field(default_factory=list)
    integrated_lufs: float | None = None
    true_peak_dbfs: float | None = None
    sample_peak_dbfs: float | None = None


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class Report:
    path: str
    profile: str
    checks: list[Check]
    media: MediaInfo | None = None
    measurements: Measurements | None = None

    @property
    def passed(self) -> bool:
        return all(check.status != "fail" for check in self.checks)

    @property
    def failures(self) -> int:
        return sum(check.status == "fail" for check in self.checks)

    @property
    def warnings(self) -> int:
        return sum(check.status == "warn" for check in self.checks)
