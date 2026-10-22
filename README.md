# video-qa

Local quality checks for rendered videos, before publishing or as a CI gate.
Detect frozen pictures, black segments, missing or silent audio, peaks near
clipping, loudness drift, and unexpected resolution, frame rate, or duration.
Useful after a Remotion render or an FFmpeg script.

[Türkçe](README.tr.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## Install

Requires Python 3.10+ and local **ffmpeg and ffprobe** binaries on PATH.
Use a full FFmpeg distribution with `freezedetect`, `blackdetect`,
`silencedetect`, `astats`, and `loudnorm` filters. See the
[FFmpeg download page](https://ffmpeg.org/download.html) for distributions.

From a checkout:

```console
python -m pip install .
video-qa check out.mp4 --profile shorts
```

Alternatively, `python -m pip install '.[ffmpeg]'` supplies an FFmpeg binary
through `imageio-ffmpeg` when ffmpeg is absent from PATH. **That extra does not
supply ffprobe**; install it separately. You can select binaries explicitly:

```console
video-qa check out.mp4 --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe
```

All decoding runs locally. The tool does not upload media, call APIs, download
binaries at runtime, or modify the input. Network protocols are disabled for
FFmpeg/ffprobe inputs. Diagnostic reports contain the input path and may contain
decoder messages; review them before sharing.

## Use

```console
video-qa check out.mp4 --profile shorts --max-freeze 1.5 --target-lufs -14
video-qa check out.mp4 --profile reels --max-duration 120 --max-silence 1
video-qa check out.mp4 --profile tiktok --format json --output report.json
video-qa check out.mp4 --profile examples/custom.toml --format junit --output junit.xml
python -m video_qa check out.mp4 --max-black 0.25 --timeout 600
```

`--format human` (default) prints a table with PASS, WARN, and FAIL rows.
JSON and JUnit contain the same checks. With `--output`, only the report file is
written; its parent directory must already exist.

| Exit code | Meaning |
| --- | --- |
| 0 | All required checks passed; warnings may be present |
| 1 | Quality failure, decoding/tool/measurement error, or report write failure |
| 2 | Invalid arguments or profile |

Analysis errors are represented as a failed `analysis` check in the selected
report format. Warnings never fail the gate. In JUnit they appear in a test's
`system-out`; only failures create `failure` elements.

## Profiles and thresholds

These are **editorial quality presets**, not promises about current upload
eligibility or official platform limits. Set your own duration and audio policy.

| Preset | Display raster | Display aspect | Average fps | Duration |
| --- | --- | --- | --- | --- |
| `shorts` | 1080×1920 | 9:16 | 24–60 | 0.1–60 seconds |
| `reels` | 1080×1920 | 9:16 | 24–60 | 0.1–90 seconds |
| `tiktok` | 1080×1920 | 9:16 | 24–60 | 0.1–180 seconds |

Common defaults:

| Setting | Default | Result when exceeded |
| --- | --- | --- |
| `max_freeze` | 1.5 seconds | Failure |
| `max_black` | 0.5 seconds | Failure |
| `max_silence` | 2 seconds | Failure |
| `target_lufs` / `lufs_tolerance` | −14 / ±2 LUFS | Warning |
| `max_peak_dbfs` | −0.1 dBFS sample peak and −0.1 dBTP true peak | Failure |
| `require_audio` | `true` | Failure if no audio stream |

Duration thresholds apply to the **longest contiguous event**, including
leading/trailing events, not total accumulated time. Equality passes. Detection
uses 1 ms minimum events for black and silence; freeze detection waits at least
one average frame period plus 1 ms to avoid treating ordinary frame gaps as
freezes. Very short repeated frames may therefore go undetected. Precision is
limited by frame/sample timing. Digital silence gives
`-inf` loudness and peaks; JSON represents this as the string `"-inf"`, never a
nonstandard JSON number. Completely silent audio fails the silence rule.

Custom TOML and JSON files are flat objects. Start from a built-in with
`extends` (defaults to `shorts`); omitted fields inherit that preset. Unknown keys,
nonfinite numbers, invalid types, and inconsistent bounds are errors. CLI
thresholds override the loaded profile.

```toml
extends = "shorts"
name = "my-render-gate"
max_duration = 75
max_freeze = 0.5
target_lufs = -14
lufs_tolerance = 2
loudness_severity = "fail"
```

Other configurable fields are `width`, `height`, `aspect_ratio` (numeric width /
height), `aspect_tolerance` (absolute ratio error, default 0.01), `min_fps`,
`max_fps`, `min_duration`, `max_black`, `max_silence`, `silence_db` (−50 dB),
`freeze_noise_db` (−60 dB), `black_pixel_threshold` (0.1), `black_picture_ratio`
(0.98), `max_peak_dbfs`, and `require_audio`. `loudness_severity` accepts `warn`
or `fail`. Examples: [TOML](examples/custom.toml), [JSON](examples/custom.json).

## How analysis works and its limits

`ffprobe` JSON supplies stream metadata. Two FFmpeg passes decode video and
audio: `freezedetect`/`blackdetect`, then `silencedetect`/`astats`/`loudnorm`.
Peaks are measured **before** loudnorm; reports use loudnorm's input measurements.
The null output is discarded. A failed subprocess or missing required audio
measurement fails the gate. `--timeout` applies separately to each subprocess
(default 300 seconds), rather than to the whole check.

Only the first playable video (excluding cover art) and first audio stream are
checked; multiple streams produce a warning. Right-angle rotation and pixel
aspect ratio affect display checks. Average fps is checked; variable frame rate
and individual timestamp continuity are not validated. Missing stream duration
falls back to container duration, so precise audio coverage cannot always be
inferred. An audio stream ending more than `max_silence` before the video fails
`audio_coverage`. Stream start offsets are not compared. Event timestamps are
relative to each selected stream's start.

Still title cards, fades, and deliberate pauses can trigger detections. Adjust
thresholds for your content. Peaks near full scale indicate clipping risk; they
do not prove that a signal was previously clipped. No speech recognition,
perceptual video assessment, codec policy, or platform API validation is done.
FFmpeg diagnostics follow the upstream
[filter documentation](https://ffmpeg.org/ffmpeg-filters.html).

## Development

```console
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python -m ruff check src tests
python -m ruff format --check src tests
python -m build
```

To test without installing the package, set `PYTHONPATH=src` in your shell first
(PowerShell: `$env:PYTHONPATH='src'`). Unit tests use stdlib `unittest`. Synthetic
integration tests generate tiny `testsrc` + `sine` videos with FFmpeg; they also
check black/frozen/silent and clipped renders. They skip if FFmpeg is unavailable;
the complete metadata-to-report integration additionally needs ffprobe on PATH.
`VIDEO_QA_TEST_FFMPEG` can select a test binary without installing the extra.
Generated test files stay under the ignored `is/tests/` directory.

CI runs lint, formatting, tests, and wheel/sdist builds on Ubuntu and Windows
with Python 3.10 and 3.14 and both FFmpeg tools installed.

## License

MIT. Copyright (c) 2026 Yusuf Berat Zengin.
