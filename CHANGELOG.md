# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-23

### Added
- Local FFmpeg freeze, black-frame, silence, sample-peak, true-peak, and integrated loudness analysis.
- Multi-pass automated defect detection evaluating display resolution, aspect ratio, frame rate, duration, and audio/video sync coverage.
- Pure `parse_ffmpeg_info` metadata fallback when `ffprobe` is not available, allowing `video-qa[ffmpeg]` to function with zero external binary dependencies.
- Concurrent two-pass decoding via `ThreadPoolExecutor` in `video_qa.analyzer.measure`, decoding video and audio streams simultaneously while maintaining deterministic report output.
- Built-in presets for Shorts, Reels, and TikTok, custom TOML/JSON profile inheritance (`extends`), and command-line threshold overrides.
- Multi-format reporting: human-readable terminal tables, strict JSON schema, and pretty-printed JUnit XML test suites for CI/CD integration.
- CLI flags: `--list-profiles` to view all preset thresholds, `--fail-on-warn` to treat warnings as pipeline failures, and `--output` for direct report export.
- Reusable GitHub Actions CI workflow example in `examples/github-workflow.yml` and sample generated reports in `examples/report.json` and `examples/junit.xml`.
- Cross-platform CI matrix on Ubuntu, Windows, and macOS across Python 3.10 and Python 3.14.
- Security and quality workflows: CodeQL Python analysis, Dependabot weekly updates, and GitHub YAML Issue forms.
- PEP 561 `py.typed` marker and package data, with strict `mypy` type checking and pytest coverage enforcement.
- Synthetic FFmpeg integration tests, captured filter log fixtures, and robustness suite covering zero-byte MP4s, rotated rasters, variable frame rate, and non-ASCII paths.

### Changed
- Decoupled mandatory `ffprobe` dependency: `video-qa` seamlessly probes container streams via `ffmpeg` when `ffprobe` is absent.
- Standardized report exit codes: 0 for pass, 1 for gate/operational failure, and 2 for argument/configuration error.

### Fixed
- Fixed trailing silence interval quirk: ignore intervals starting at or beyond stream duration and zero-length events to prevent false silence failures when `max_silence` is 0.

[Unreleased]: https://github.com/YusufBeratZengin/video-qa/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YusufBeratZengin/video-qa/releases/tag/v0.1.0
