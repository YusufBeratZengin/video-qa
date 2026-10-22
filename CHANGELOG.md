# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Add pure `parse_ffmpeg_info` parser in `video_qa.parsers` to extract video dimensions, fps, duration, audio presence, SAR, and rotation from `ffmpeg -hide_banner -i` stderr when `ffprobe` is absent.
- Add `probe_source` field to `Report`, stating whether `"ffprobe"` or `"ffmpeg"` was used in human, JSON, and JUnit reports.
- Add CLI flag `--list-profiles` to display built-in presets and threshold configurations.
- Add CLI flag `--fail-on-warn` to treat warnings as failures and exit with code 1.
- Add concurrent two-pass decoding via `ThreadPoolExecutor` in `video_qa.analyzer.measure`, decoding video and audio streams simultaneously while maintaining deterministic report output.
- Add release workflow in `.github/workflows/release.yml` for `v*` tags using PyPI trusted publishing (`id-token: write`, environment `pypi`) and GitHub releases.
- Add PEP 561 `py.typed` marker and package data, with strict `mypy` type checking in dev dependencies and CI.
- Add enhanced pyproject metadata: Python 3.10-3.14 classifiers, SPDX license expression, `license-files`, `Source` and `Changelog` URLs, and multimedia keywords.
- Add community files: `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), GitHub issue templates (`bug_report.md`, `feature_request.md`), and pull request template (`pull_request_template.md`).
- Add reusable GitHub Actions CI workflow example in `examples/github-workflow.yml`.
- Add script `scripts/make_examples.py` generating `examples/report.json` and `examples/junit.xml`.
- Add real captured report and JUnit XML excerpts to bilingual READMEs.
- Add live CI status and MIT license badges to `README.md` and `README.tr.md`.
- Add synthetic filter pipeline integration tests for clean clips, black segments, frozen sections, silent audio, clipped sine audio, and audio presence.
- Add robustness tests covering zero-byte MP4s, audio-only inputs, 90-degree rotated video raster swapping, variable frame rate, sub-0.1s clips, and non-ASCII paths with Turkish characters on Windows.

### Changed
- Decouple mandatory `ffprobe` dependency: `video-qa` now seamlessly probes via `ffmpeg` when `ffprobe` is not installed on PATH, making `video-qa[ffmpeg]` fully functional on its own.
- Add `ET.indent` pretty-printing to `junit_report`.

### Fixed
- Fix trailing silence interval quirk: ignore intervals starting at or beyond stream duration and zero-length events to prevent false silence failures when `max_silence` is 0.

## [0.1.0] — 2026-10-22

### Added
- Add local FFmpeg freeze, black-frame, silence, sample-peak, true-peak, and
  integrated loudness analysis, with ffprobe JSON metadata parsing.
- Add resolution, display aspect, average frame rate, duration, audio presence,
  and audio coverage rules.
- Add editable Shorts, Reels, and TikTok presets, custom TOML/JSON profiles,
  and command-line threshold overrides.
- Add human, strict JSON, and JUnit XML reports with separate warnings and
  nonzero exit codes for failed quality gates and analysis errors.
- Add captured parser fixtures, unit tests, synthetic FFmpeg integration tests,
  bilingual documentation, and Ubuntu/Windows CI.

[Unreleased]: https://github.com/YusufBeratZengin/video-qa/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YusufBeratZengin/video-qa/releases/tag/v0.1.0
