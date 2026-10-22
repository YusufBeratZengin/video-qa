# Contributing

Please open an issue at
[YusufBeratZengin/video-qa](https://github.com/YusufBeratZengin/video-qa/issues)
before a large change. Small fixes and focused tests are welcome.

## Set up

Use Python 3.10+ and install FFmpeg **and ffprobe** on PATH, including the analysis
filters documented in the README.

```console
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on Linux/macOS or
`.venv\Scripts\Activate.ps1` in PowerShell, then:

```console
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python -m ruff check src tests
python -m ruff format --check src tests
python -m build
```

To run without an install, set `PYTHONPATH=src` first
(PowerShell: `$env:PYTHONPATH='src'`). No third-party test runner is required.
Without FFmpeg the synthetic integration tests skip. Without ffprobe the full
end-to-end test skips, but filter integration can still run with FFmpeg.
`VIDEO_QA_TEST_FFMPEG` selects a test binary. A skipped test is not evidence that
integration passed. Generated media stays under ignored `is/tests/`.

## Changes

- Keep parsers pure and add fixtures for new diagnostic formats.
- Use synthetic media and anonymized log excerpts. Never include private videos,
  real personal data, credentials, or absolute workstation paths.
- Record the FFmpeg version and capture command when adding a fixture. Retain
  measured values and event order; remove memory addresses and source paths.
- Cover rule boundary behavior and error paths when changing a gate.
- Update both READMEs when public behavior changes, and add a changelog entry.
- Keep commits small and use Conventional Commits, for example
  `fix: close trailing freeze intervals` or `test: cover rational frame rates`.

Pull requests should explain the observable behavior, include test commands and
results, and disclose skipped checks. CI runs Python 3.10 and 3.14 on Ubuntu and
Windows. Contributions are provided under the repository's MIT license.
