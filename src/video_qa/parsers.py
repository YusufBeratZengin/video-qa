"""Pure parsers for ffprobe JSON and FFmpeg filter diagnostics.

No subprocesses run here. Unknown or incomplete measurements raise ParseError;
an empty event list is valid because event filters are silent on clean inputs.
"""

from __future__ import annotations

import json
import math
import re
from fractions import Fraction
from typing import Any

from video_qa.models import Interval, MediaInfo

NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
LEVEL = rf"(?:{NUMBER}|[-+]?inf|nan)"


class ParseError(ValueError):
    """A required measurement is absent or invalid."""


def _positive(value: Any) -> float | None:
    try:
        result = float(Fraction(str(value)))
    except (ValueError, ZeroDivisionError, TypeError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def parse_probe(text: str) -> MediaInfo:
    """Read the first non-cover video and first audio stream, matching mapping."""
    try:
        data = json.loads(text)
        streams = data["streams"]
        videos = [
            s
            for s in streams
            if s.get("codec_type") == "video"
            and not s.get("disposition", {}).get("attached_pic", 0)
        ]
        audios = [s for s in streams if s.get("codec_type") == "audio"]
        if not videos:
            raise ParseError("No playable video stream found")
        video = videos[0]
        width, height = int(video["width"]), int(video["height"])
        fps = _positive(video.get("avg_frame_rate")) or _positive(video.get("r_frame_rate"))
        container_duration = _positive(data.get("format", {}).get("duration"))
        duration = _positive(video.get("duration")) or container_duration
        if min(width, height) <= 0 or fps is None or duration is None:
            raise ParseError("Video dimensions, frame rate and duration must be positive")
        rotation = int(float(video.get("tags", {}).get("rotate", 0)))
        for side in video.get("side_data_list", []):
            if "rotation" in side:
                rotation = int(float(side["rotation"]))
        if rotation % 90:
            raise ParseError("Only right-angle display rotation is supported")
        sar = str(video.get("sample_aspect_ratio", "1:1")).replace(":", "/")
        audio_duration = (
            _positive(audios[0].get("duration")) or container_duration or duration
            if audios
            else None
        )
        return MediaInfo(
            width=width,
            height=height,
            fps=fps,
            duration=max(duration, audio_duration or 0, container_duration or 0),
            has_audio=bool(audios),
            video_duration=duration,
            audio_duration=audio_duration,
            sample_aspect_ratio=_positive(sar) or 1.0,
            rotation=rotation,
            video_streams=len(videos),
            audio_streams=len(audios),
        )
    except (KeyError, TypeError, AttributeError, ValueError, OverflowError) as exc:
        if isinstance(exc, ParseError):
            raise
        raise ParseError(f"Invalid ffprobe JSON: {exc}") from exc


def parse_intervals(text: str, kind: str, duration: float) -> list[Interval]:
    """Pair events; close an open freeze/silence/black interval at stream EOF.

    Log prefixes, CRLF, scientific notation, and multiple events per line are
    accepted. Durations printed by filters are ignored in favor of timestamps.
    """
    if kind not in {"freeze", "black", "silence"}:
        raise ValueError(f"Unknown interval kind: {kind}")
    pattern = re.compile(rf"\b{kind}_(start|end)\s*:\s*({NUMBER})")
    result: list[Interval] = []
    start: float | None = None
    for event, raw in pattern.findall(text):
        timestamp = min(duration, max(0.0, float(raw)))
        if event == "start":
            start = timestamp if start is None else min(start, timestamp)
        elif start is not None:
            if timestamp < start:
                raise ParseError(f"{kind} interval ends before it starts")
            result.append(Interval(start, timestamp))
            start = None
    if start is not None:
        result.append(Interval(start, duration))
    return result


def _level(value: Any) -> float:
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ParseError(f"Invalid audio level: {value}") from exc
    if math.isnan(result) or result == math.inf:
        raise ParseError(f"Invalid audio level: {value}")
    return result  # -inf is a real measurement of digital silence.


def parse_loudnorm(text: str) -> tuple[float, float]:
    """Extract *input* LUFS and true peak, never normalized output values."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            data, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "input_i" in data and "input_tp" in data:
            return _level(data["input_i"]), _level(data["input_tp"])
    raise ParseError("Missing loudnorm input_i/input_tp JSON measurements")


def parse_astats(text: str) -> float:
    """Use the highest channel/overall sample peak (astats reset must be 0)."""
    levels = re.findall(rf"\bPeak level dB:\s*({LEVEL})", text, flags=re.IGNORECASE)
    if not levels:
        raise ParseError("Missing astats Peak level dB measurement")
    return max(_level(level) for level in levels)
