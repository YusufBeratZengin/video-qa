"""Robustness tests for edge-case files, non-ASCII paths, and corrupt inputs."""

import contextlib
import io
import os
import subprocess
import unittest
from pathlib import Path

from tests.support import temporary_directory
from video_qa.analyzer import AnalysisError, find_ffmpeg, probe_ffmpeg
from video_qa.cli import main


class RobustnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = find_ffmpeg(os.environ.get("VIDEO_QA_TEST_FFMPEG"))
            subprocess.run([cls.ffmpeg, "-version"], capture_output=True, check=True, timeout=15)
        except (AnalysisError, OSError, subprocess.SubprocessError) as exc:
            raise unittest.SkipTest(f"FFmpeg unavailable: {exc}") from exc

    def invoke(self, args: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_corrupt_zero_byte_mp4(self):
        with temporary_directory() as directory:
            zero_file = Path(directory) / "corrupt_zero.mp4"
            zero_file.write_bytes(b"")
            code, stdout, stderr = self.invoke(["check", str(zero_file), "--ffmpeg", self.ffmpeg])
            self.assertEqual(code, 1)
            self.assertIn("FAIL", stdout)
            self.assertIn("analysis", stdout)
            self.assertNotIn("Traceback", stdout)
            self.assertNotIn("Traceback", stderr)

    def test_file_without_video_stream(self):
        with temporary_directory() as directory:
            audio_file = Path(directory) / "audio_only.mkv"
            subprocess.run(
                [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440",
                    "-t",
                    "1",
                    "-c:a",
                    "pcm_s16le",
                    str(audio_file),
                ],
                capture_output=True,
                check=True,
                timeout=15,
            )
            code, stdout, stderr = self.invoke(["check", str(audio_file), "--ffmpeg", self.ffmpeg])
            self.assertEqual(code, 1)
            self.assertIn("No playable video stream found", stdout)
            self.assertNotIn("Traceback", stdout)
            self.assertNotIn("Traceback", stderr)

    def test_rotated_video_swaps_display_dimensions(self):
        with temporary_directory() as directory:
            rot_file = Path(directory) / "rotated.mkv"
            # 1920x1080 raster with 90-degree rotation metadata -> 1080x1920 display raster
            subprocess.run(
                [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-y",
                    "-f",
                    "lavfi",
                    "-display_rotation",
                    "90",
                    "-noautorotate",
                    "-i",
                    "testsrc=size=1920x1080:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440",
                    "-t",
                    "1",
                    "-c:v",
                    "ffv1",
                    "-c:a",
                    "pcm_s16le",
                    str(rot_file),
                ],
                capture_output=True,
                check=True,
                timeout=20,
            )
            media = probe_ffmpeg(rot_file, self.ffmpeg, timeout=15)
            self.assertEqual((media.width, media.height), (1920, 1080))
            self.assertEqual(abs(media.rotation), 90)
            code, stdout, stderr = self.invoke(
                ["check", str(rot_file), "--profile", "shorts", "--ffmpeg", self.ffmpeg]
            )
            self.assertIn(
                "PASS    resolution      Display raster 1080x1920; expected 1080x1920",
                stdout,
            )
            self.assertNotIn("Traceback", stdout)
            self.assertNotIn("Traceback", stderr)

    def test_variable_frame_rate(self):
        with temporary_directory() as directory:
            vfr_file = Path(directory) / "vfr.mp4"
            subprocess.run(
                [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=1080x1920:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440",
                    "-vf",
                    "mpdecimate",
                    "-fps_mode",
                    "vfr",
                    "-t",
                    "1",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    str(vfr_file),
                ],
                capture_output=True,
                check=True,
                timeout=20,
            )
            code, stdout, stderr = self.invoke(
                ["check", str(vfr_file), "--profile", "shorts", "--ffmpeg", self.ffmpeg]
            )
            self.assertIn("fps", stdout)
            self.assertNotIn("Traceback", stdout)
            self.assertNotIn("Traceback", stderr)

    def test_extremely_short_clip(self):
        with temporary_directory() as directory:
            short_file = Path(directory) / "too_short.mkv"
            subprocess.run(
                [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=1080x1920:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440",
                    "-t",
                    "0.05",
                    "-c:v",
                    "ffv1",
                    "-c:a",
                    "pcm_s16le",
                    str(short_file),
                ],
                capture_output=True,
                check=True,
                timeout=20,
            )
            code, stdout, stderr = self.invoke(
                ["check", str(short_file), "--profile", "shorts", "--ffmpeg", self.ffmpeg]
            )
            self.assertEqual(code, 1)
            self.assertIn("FAIL    duration", stdout)
            self.assertIn("allowed 0.1-60s", stdout)
            self.assertNotIn("Traceback", stdout)
            self.assertNotIn("Traceback", stderr)

    def test_path_with_spaces_and_turkish_characters(self):
        with temporary_directory() as directory:
            folder = Path(directory) / "klasör Türkçe çşğı"
            folder.mkdir()
            clip_file = folder / "klip Türkçe çşğı.mkv"
            subprocess.run(
                [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=1080x1920:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440",
                    "-t",
                    "1",
                    "-c:v",
                    "ffv1",
                    "-c:a",
                    "pcm_s16le",
                    str(clip_file),
                ],
                capture_output=True,
                check=True,
                timeout=20,
            )
            code, stdout, stderr = self.invoke(
                ["check", str(clip_file), "--profile", "shorts", "--ffmpeg", self.ffmpeg]
            )
            self.assertEqual(code, 0)
            self.assertIn("PASS: 0 failure(s)", stdout)
            self.assertNotIn("Traceback", stdout)
            self.assertNotIn("Traceback", stderr)
