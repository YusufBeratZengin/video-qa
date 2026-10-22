"""Run local binaries without a shell; inputs are decoded but never modified."""

from __future__ import annotations

import concurrent.futures
import os
import shutil
import subprocess
from pathlib import Path

from video_qa.engine import evaluate
from video_qa.models import Measurements, MediaInfo, Report
from video_qa.parsers import (
    parse_astats,
    parse_ffmpeg_info,
    parse_intervals,
    parse_loudnorm,
    parse_probe,
)
from video_qa.profiles import Profile


class AnalysisError(RuntimeError):
    """Missing tools, failed decoding, or analysis timeout."""


def find_ffmpeg(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise AnalysisError("ffmpeg not found; install FFmpeg or video-qa[ffmpeg]") from exc
    try:
        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except (RuntimeError, OSError) as exc:
        raise AnalysisError(f"Cannot locate optional FFmpeg binary: {exc}") from exc


def find_ffprobe(explicit: str | None = None) -> str:
    found = explicit or shutil.which("ffprobe")
    if not found:
        raise AnalysisError(
            "ffprobe not found; install the FFmpeg tools and put ffprobe on PATH "
            "or pass --ffprobe. The imageio-ffmpeg extra supplies only ffmpeg."
        )
    return found


def _run(args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "LC_ALL": "C", "AV_LOG_FORCE_NOCOLOR": "1"}
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AnalysisError(f"{Path(args[0]).name} exceeded {timeout:g}s timeout") from exc
    except OSError as exc:
        raise AnalysisError(f"Cannot execute {Path(args[0]).name}: {exc}") from exc
    if result.returncode:
        detail = result.stderr.strip()[-2000:]
        raise AnalysisError(f"{Path(args[0]).name} exited {result.returncode}: {detail}")
    return result


def probe(path: Path, ffprobe: str, timeout: float) -> MediaInfo:
    result = _run(
        [
            ffprobe,
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path.resolve()),
        ],
        timeout,
    )
    return parse_probe(result.stdout)


def probe_ffmpeg(path: Path, ffmpeg: str, timeout: float) -> MediaInfo:
    env = {**os.environ, "LC_ALL": "C", "AV_LOG_FORCE_NOCOLOR": "1"}
    args = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        str(path.resolve()),
    ]
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AnalysisError(f"{Path(args[0]).name} exceeded {timeout:g}s timeout") from exc
    except OSError as exc:
        raise AnalysisError(f"Cannot execute {Path(args[0]).name}: {exc}") from exc
    return parse_ffmpeg_info(result.stderr)


def measure(
    path: Path, media: MediaInfo, profile: Profile, ffmpeg: str, timeout: float = 300
) -> Measurements:
    """Measure selected streams in two decoding passes, audio at original gain."""
    common = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-nostats",
        "-loglevel",
        "info",
        "-xerror",
        "-protocol_whitelist",
        "file,pipe",
        "-noautorotate",
        "-i",
        str(path.resolve()),
    ]
    # Less than one frame would classify the ordinary gap between moving
    # frames as a freeze. Keep some margin for rounded container timestamps.
    freeze_detection = max(1 / media.fps + 0.001, min(profile.max_freeze, 0.5))
    video_filter = (
        "setpts=PTS-STARTPTS,"
        f"freezedetect=n={profile.freeze_noise_db}dB:d={freeze_detection},"
        f"blackdetect=d=0.001:pix_th={profile.black_pixel_threshold}"
        f":pic_th={profile.black_picture_ratio}"
    )
    video_args = common + [
        "-map",
        "0:V:0",
        "-an",
        "-sn",
        "-dn",
        "-vf",
        video_filter,
        "-f",
        "null",
        "-",
    ]
    if not media.has_audio:
        video_log = _run(video_args, timeout).stderr
        return Measurements(
            freezes=parse_intervals(video_log, "freeze", media.video_duration),
            black=parse_intervals(video_log, "black", media.video_duration),
        )

    audio_filter = (
        "asetpts=PTS-STARTPTS,"
        f"silencedetect=n={profile.silence_db}dB:d=0.001,"
        "astats=reset=0,"
        f"loudnorm=I={profile.target_lufs}:print_format=json"
    )
    audio_args = common + [
        "-map",
        "0:a:0",
        "-vn",
        "-sn",
        "-dn",
        "-af",
        audio_filter,
        "-f",
        "null",
        "-",
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        video_future = executor.submit(_run, video_args, timeout)
        audio_future = executor.submit(_run, audio_args, timeout)
        video_log = video_future.result().stderr
        audio_log = audio_future.result().stderr

    freezes = parse_intervals(video_log, "freeze", media.video_duration)
    black = parse_intervals(video_log, "black", media.video_duration)
    lufs, true_peak = parse_loudnorm(audio_log)
    return Measurements(
        freezes=freezes,
        black=black,
        silence=parse_intervals(audio_log, "silence", media.audio_duration or media.duration),
        integrated_lufs=lufs,
        true_peak_dbfs=true_peak,
        sample_peak_dbfs=parse_astats(audio_log),
    )


def analyze(
    path: Path,
    profile: Profile,
    *,
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
    timeout: float = 300,
) -> Report:
    if not path.is_file():
        raise AnalysisError(f"Input is not a regular file: {path}")
    probe_source = "ffprobe"
    resolved_ffprobe = ffprobe or shutil.which("ffprobe")
    if resolved_ffprobe:
        media = probe(path, resolved_ffprobe, timeout)
        probe_source = "ffprobe"
    else:
        resolved_ffmpeg = find_ffmpeg(ffmpeg)
        media = probe_ffmpeg(path, resolved_ffmpeg, timeout)
        probe_source = "ffmpeg"
    resolved_ffmpeg = find_ffmpeg(ffmpeg)
    measured = measure(path, media, profile, resolved_ffmpeg, timeout)
    return evaluate(str(path), media, measured, profile, probe_source=probe_source)
