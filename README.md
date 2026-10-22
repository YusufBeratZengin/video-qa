# video-qa

[![CI](https://github.com/YusufBeratZengin/video-qa/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/video-qa/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Local quality checks for rendered videos, before publishing or as a CI gate.
Detect frozen pictures, black segments, missing or silent audio, peaks near
clipping, loudness drift, and unexpected resolution, frame rate, or duration.
Useful after a Remotion render or an FFmpeg script.

[Türkçe](README.tr.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## Install

Requires Python 3.10+ and a local FFmpeg installation. When `ffprobe` is present
on PATH or specified via `--ffprobe`, it is used to extract container and stream
metadata. If `ffprobe` is absent, `video-qa` automatically falls back to parsing
`ffmpeg -hide_banner -i` output, keeping the tool fully functional without a
separate ffprobe binary.

Use a full FFmpeg distribution with `freezedetect`, `blackdetect`,
`silencedetect`, `astats`, and `loudnorm` filters. See the
[FFmpeg download page](https://ffmpeg.org/download.html) for distributions.

From a checkout:

```console
python -m pip install .
video-qa check out.mp4 --profile shorts
```

Alternatively, `python -m pip install '.[ffmpeg]'` supplies an FFmpeg binary
through `imageio-ffmpeg` when ffmpeg is absent from PATH. While `imageio-ffmpeg`
only provides `ffmpeg` (not `ffprobe`), `video-qa` seamlessly operates using its
built-in FFmpeg metadata fallback. You can also specify binaries explicitly:

```console
video-qa check out.mp4 --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe
```

All decoding runs locally. The tool does not upload media, call APIs, download
binaries at runtime, or modify the input. Network protocols are disabled for
FFmpeg/ffprobe inputs. Diagnostic reports contain the input path and may contain
decoder messages; review them before sharing.

## Use

```console
video-qa --list-profiles
video-qa check out.mp4 --profile shorts --max-freeze 1.5 --target-lufs -14
video-qa check out.mp4 --profile reels --max-duration 120 --max-silence 1
video-qa check out.mp4 --profile tiktok --format json --output report.json
video-qa check out.mp4 --profile examples/custom.toml --format junit --output junit.xml
video-qa check out.mp4 --fail-on-warn
python -m video_qa check out.mp4 --max-black 0.25 --timeout 600
```

CLI flags:
* `--list-profiles`: Print all built-in profiles and their default thresholds, then exit.
* `--fail-on-warn`: Treat warnings (such as loudness deviations or multi-stream notices) as failures (exit code 1).
* `--format`: Choose between `human` (default table), `json` (strict JSON schema), or `junit` (JUnit XML).
* `--output`: Write report directly to a file instead of stdout.

| Exit code | Meaning |
| --- | --- |
| 0 | All required checks passed; warnings may be present (unless `--fail-on-warn` is used) |
| 1 | Quality failure, decoding/tool/measurement error, `--fail-on-warn` with warnings, or report write failure |
| 2 | Invalid arguments or profile configuration |

Analysis errors are represented as a failed `analysis` check in the selected
report format. Warnings never fail the gate by default. In JUnit they appear in a test's
`system-out`; only failures create `failure` elements.

## Example output

### Human report (`--format human`)

```text
out.mp4 (profile: shorts, probe: ffmpeg)
STATUS  CHECK           DETAIL
PASS    resolution      Display raster 1080x1920; expected 1080x1920
PASS    aspect_ratio    Display aspect 0.56250; expected 0.56250
PASS    fps             Average 30.000 fps; allowed 24-60
PASS    duration        3.000s; allowed 0.1-60s
PASS    freeze          Longest 0.000s across 0 event(s); allowed <= 1.5s
PASS    black           Longest 0.000s across 0 event(s); allowed <= 0.5s
PASS    silence         Longest 0.000s across 0 event(s); allowed <= 2s
PASS    audio           Audio stream present
PASS    clipping        Sample peak -17.687953 dBFS; allowed <= -0.1 dBFS
PASS    true_peak       True peak -17.69 dBTP; allowed <= -0.1 dBTP
WARN    loudness        Integrated -21.8 LUFS; target -14 +/- 2
PASS    audio_coverage  Video extends 0.000s beyond audio; allowed <= 2s
PASS: 0 failure(s), 1 warning(s)
```

### JUnit XML report (`--format junit`)

```xml
<?xml version='1.0' encoding='utf-8'?>
<testsuite name="video-qa" tests="12" failures="0" errors="0" skipped="0">
  <properties>
    <property name="input" value="out.mp4" />
    <property name="profile" value="shorts" />
    <property name="probe_source" value="ffmpeg" />
    <property name="warnings" value="1" />
  </properties>
  <testcase classname="video_qa" name="resolution" />
  <testcase classname="video_qa" name="aspect_ratio" />
  <testcase classname="video_qa" name="fps" />
  <testcase classname="video_qa" name="duration" />
  <testcase classname="video_qa" name="freeze" />
  <testcase classname="video_qa" name="black" />
  <testcase classname="video_qa" name="silence" />
  <testcase classname="video_qa" name="audio" />
  <testcase classname="video_qa" name="clipping" />
  <testcase classname="video_qa" name="true_peak" />
  <testcase classname="video_qa" name="loudness">
    <system-out>WARNING: Integrated -21.8 LUFS; target -14 +/- 2</system-out>
  </testcase>
  <testcase classname="video_qa" name="audio_coverage" />
</testsuite>
```

Full sample files generated by `scripts/make_examples.py` are saved in
[examples/report.json](examples/report.json) and [examples/junit.xml](examples/junit.xml).

## Continuous Integration (GitHub Actions)

You can run `video-qa` as an automated gate in your CI pipeline after rendering
videos with Remotion or FFmpeg. See [examples/github-workflow.yml](examples/github-workflow.yml)
for a complete reusable workflow.

```yaml
- name: Run video-qa quality gate
  run: video-qa check out.mp4 --profile shorts --format junit --output junit.xml

- name: Upload JUnit report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: video-qa-junit-report
    path: junit.xml
```

## Profiles and thresholds

These are **editorial quality presets**, not promises about current upload
eligibility or official platform limits. Set your own duration and audio policy.
You can view these anytime with `video-qa --list-profiles`.

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

## How analysis works, performance, and limits

Stream metadata is obtained from `ffprobe` JSON or `ffmpeg -hide_banner -i` stderr.
Decoding runs in two concurrent FFmpeg passes via a thread pool:
`freezedetect`/`blackdetect` on video, and `silencedetect`/`astats`/`loudnorm` on audio.
Running both passes concurrently maximizes throughput on multi-core systems while
preserving strict per-process `--timeout` semantics and deterministic report output.
On modern hardware, full analysis of a 60-second 1080×1920 synthetic clip takes
approximately 2.7 seconds (~22× faster than realtime).

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
python -m mypy
python -m build && python -m twine check dist/*
```

To test without installing the package, set `PYTHONPATH=src` in your shell first
(PowerShell: `$env:PYTHONPATH='src'`). Unit tests use stdlib `unittest`. Synthetic
integration tests generate tiny `testsrc` + `sine` videos with FFmpeg; they also
check black/frozen/silent and clipped renders. They skip if FFmpeg is unavailable.
`VIDEO_QA_TEST_FFMPEG` can select a test binary without installing the extra.
Generated test files stay under the ignored `is/tests/` directory.

CI runs lint, formatting, static typing with `mypy`, tests, and wheel/sdist builds
on Ubuntu and Windows with Python 3.10 and 3.14.

## License

MIT. Copyright (c) 2026 Yusuf Berat Zengin.
