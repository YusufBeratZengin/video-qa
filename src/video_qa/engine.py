"""Deterministic quality rules; warnings do not fail the gate."""

from __future__ import annotations

import math

from video_qa.models import Check, Measurements, MediaInfo, Report
from video_qa.profiles import Profile


def evaluate(
    path: str,
    media: MediaInfo,
    measured: Measurements,
    profile: Profile,
    probe_source: str = "ffprobe",
) -> Report:
    checks: list[Check] = []

    def add(name: str, passed: bool, message: str, severity: str = "fail") -> None:
        checks.append(Check(name, "pass" if passed else severity, message))

    width, height = media.width, media.height
    if media.rotation % 180:
        width, height = height, width
    add(
        "resolution",
        (width, height) == (profile.width, profile.height),
        f"Display raster {width}x{height}; expected {profile.width}x{profile.height}",
    )
    add(
        "aspect_ratio",
        abs(media.display_aspect_ratio - profile.aspect_ratio) <= profile.aspect_tolerance,
        f"Display aspect {media.display_aspect_ratio:.5f}; expected {profile.aspect_ratio:.5f}",
    )
    add(
        "fps",
        profile.min_fps <= media.fps <= profile.max_fps,
        f"Average {media.fps:.3f} fps; allowed {profile.min_fps:g}-{profile.max_fps:g}",
    )
    add(
        "duration",
        profile.min_duration <= media.duration <= profile.max_duration,
        f"{media.duration:.3f}s; allowed {profile.min_duration:g}-{profile.max_duration:g}s",
    )
    for name, intervals, limit in (
        ("freeze", measured.freezes, profile.max_freeze),
        ("black", measured.black, profile.max_black),
        ("silence", measured.silence, profile.max_silence),
    ):
        if name == "silence" and not media.has_audio:
            continue
        longest = max((interval.duration for interval in intervals), default=0.0)
        add(
            name,
            longest <= limit + 1e-6,
            f"Longest {longest:.3f}s across {len(intervals)} event(s); allowed <= {limit:g}s",
        )
    add(
        "audio",
        media.has_audio or not profile.require_audio,
        "Audio stream present" if media.has_audio else "No audio stream",
        "fail" if profile.require_audio else "warn",
    )
    if media.has_audio:
        peak = measured.sample_peak_dbfs
        add(
            "clipping",
            peak is not None and not math.isnan(peak) and peak <= profile.max_peak_dbfs,
            f"Sample peak {peak} dBFS; allowed <= {profile.max_peak_dbfs:g} dBFS",
        )
        true_peak = measured.true_peak_dbfs
        add(
            "true_peak",
            true_peak is not None
            and not math.isnan(true_peak)
            and true_peak <= profile.max_peak_dbfs,
            f"True peak {true_peak} dBTP; allowed <= {profile.max_peak_dbfs:g} dBTP",
        )
        lufs = measured.integrated_lufs
        add(
            "loudness",
            lufs is not None
            and math.isfinite(lufs)
            and abs(lufs - profile.target_lufs) <= profile.lufs_tolerance,
            f"Integrated {lufs} LUFS; target {profile.target_lufs:g}"
            f" +/- {profile.lufs_tolerance:g}",
            profile.loudness_severity,
        )
        # Unknown channel duration falls back to the container duration in ffprobe.
        if media.audio_duration is not None:
            gap = max(0.0, media.video_duration - media.audio_duration)
            add(
                "audio_coverage",
                gap <= profile.max_silence + 1e-6,
                f"Video extends {gap:.3f}s beyond audio; allowed <= {profile.max_silence:g}s",
            )
    if media.video_streams > 1 or media.audio_streams > 1:
        checks.append(Check("streams", "warn", "Only first playable video and first audio checked"))
    return Report(path, profile.name, checks, media, measured, probe_source=probe_source)
