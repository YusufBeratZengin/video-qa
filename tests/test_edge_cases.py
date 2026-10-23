import argparse
import io
import json
import math
import runpy
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from video_qa.analyzer import (
    AnalysisError,
    find_ffmpeg,
    find_ffprobe,
    probe,
    probe_ffmpeg,
)
from video_qa.cli import _timeout, main
from video_qa.parsers import ParseError, _level, parse_intervals, parse_probe


class EdgeCaseTests(unittest.TestCase):
    def test_main_module_execution(self):
        result = subprocess.run(
            [sys.executable, "-m", "video_qa", "--list-profiles"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Built-in profiles and thresholds:", result.stdout)

        # Also run in-process for 100% __main__.py line coverage
        with patch.object(sys, "argv", ["video-qa", "--list-profiles"]):
            with patch("sys.stdout", new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as exit_ctx:
                    runpy.run_module("video_qa.__main__", run_name="__main__")
                self.assertEqual(exit_ctx.exception.code, 0)

    def test_timeout_helper(self):
        self.assertEqual(_timeout("15.5"), 15.5)
        with self.assertRaises(argparse.ArgumentTypeError):
            _timeout("-5")
        with self.assertRaises(argparse.ArgumentTypeError):
            _timeout("0")
        with self.assertRaises(argparse.ArgumentTypeError):
            _timeout("nan")
        with self.assertRaises(argparse.ArgumentTypeError):
            _timeout("inf")

    def test_find_ffmpeg_branches(self):
        with patch("shutil.which", return_value="/custom/ffmpeg"):
            self.assertEqual(find_ffmpeg(), "/custom/ffmpeg")

        with patch("shutil.which", return_value=None):
            with patch.dict(sys.modules, {"imageio_ffmpeg": None}):
                with self.assertRaises(AnalysisError) as ctx:
                    find_ffmpeg()
                self.assertIn("ffmpeg not found", str(ctx.exception))

        mock_imageio = MagicMock()
        mock_imageio.get_ffmpeg_exe.side_effect = RuntimeError("binary missing")
        with patch("shutil.which", return_value=None):
            with patch.dict(sys.modules, {"imageio_ffmpeg": mock_imageio}):
                with self.assertRaises(AnalysisError) as ctx:
                    find_ffmpeg()
                self.assertIn("Cannot locate optional FFmpeg binary", str(ctx.exception))

    def test_find_ffprobe_branches(self):
        self.assertEqual(find_ffprobe("/opt/ffprobe"), "/opt/ffprobe")
        with patch("shutil.which", return_value=None):
            with self.assertRaises(AnalysisError) as ctx:
                find_ffprobe()
            self.assertIn("ffprobe not found", str(ctx.exception))

    def test_probe_with_ffprobe(self):
        sample_json = json.dumps(
            {
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 1080,
                        "height": 1920,
                        "avg_frame_rate": "30/1",
                        "duration": "10.0",
                    }
                ],
                "format": {"duration": "10.0"},
            }
        )
        mock_res = MagicMock(stdout=sample_json)
        with patch("video_qa.analyzer._run", return_value=mock_res):
            info = probe(Path("clip.mp4"), "ffprobe", 30)
            self.assertEqual(info.width, 1080)
            self.assertEqual(info.height, 1920)
            self.assertEqual(info.fps, 30.0)

    def test_probe_ffmpeg_errors(self):
        timeout_err = subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=5)
        with patch("subprocess.run", side_effect=timeout_err):
            with self.assertRaises(AnalysisError) as ctx:
                probe_ffmpeg(Path("clip.mp4"), "ffmpeg", 5)
            self.assertIn("exceeded 5s timeout", str(ctx.exception))

        with patch("subprocess.run", side_effect=OSError("permission denied")):
            with self.assertRaises(AnalysisError) as ctx:
                probe_ffmpeg(Path("clip.mp4"), "ffmpeg", 5)
            self.assertIn("Cannot execute", str(ctx.exception))

    def test_cli_no_command_returns_two(self):
        self.assertEqual(main([]), 2)

    def test_cli_check_without_input_exits_two(self):
        with self.assertRaises(SystemExit) as exit_ctx:
            main(["check"])
        self.assertEqual(exit_ctx.exception.code, 2)

    def test_cli_output_write_error(self):
        with patch("video_qa.cli.analyze") as mock_analyze:
            mock_analyze.return_value = MagicMock(passed=True, warnings=0)
            with patch.object(Path, "write_text", side_effect=OSError("disk full")):
                code = main(["check", "dummy.mp4", "--output", "report.txt"])
                self.assertEqual(code, 1)

    def test_cli_samefile_detected(self):
        with patch("video_qa.cli.analyze") as mock_analyze:
            mock_analyze.return_value = MagicMock(passed=True, warnings=0)
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "samefile", return_value=True):
                    with self.assertRaises(SystemExit) as exit_ctx:
                        main(["check", "a.mp4", "--output", "alias_a.mp4"])
                    self.assertEqual(exit_ctx.exception.code, 2)

    def test_parse_probe_unsupported_rotation(self):
        sample = {
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                    "duration": "5",
                    "tags": {"rotate": "45"},
                }
            ],
            "format": {"duration": "5"},
        }
        with self.assertRaises(ParseError) as ctx:
            parse_probe(json.dumps(sample))
        self.assertIn("Only right-angle display rotation", str(ctx.exception))

    def test_parse_intervals_invalid_kind(self):
        with self.assertRaises(ValueError) as ctx:
            parse_intervals("log", "unknown", 10.0)
        self.assertIn("Unknown interval kind", str(ctx.exception))

    def test_level_invalid_values(self):
        with self.assertRaises(ParseError):
            _level("not_a_number")
        with self.assertRaises(ParseError):
            _level(math.nan)
        with self.assertRaises(ParseError):
            _level(math.inf)


if __name__ == "__main__":
    unittest.main()
