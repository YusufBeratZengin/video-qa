"""Real decoding tests. No downloads, network, or external media fixtures."""

import os
import shutil
import subprocess
import unittest
from pathlib import Path

from tests.support import temporary_directory
from video_qa.analyzer import AnalysisError, analyze, find_ffmpeg, measure
from video_qa.engine import evaluate
from video_qa.models import MediaInfo
from video_qa.profiles import Profile


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = find_ffmpeg(os.environ.get("VIDEO_QA_TEST_FFMPEG"))
            subprocess.run([cls.ffmpeg, "-version"], capture_output=True, check=True, timeout=15)
        except (AnalysisError, OSError, subprocess.SubprocessError) as exc:
            raise unittest.SkipTest(f"FFmpeg unavailable: {exc}") from exc
        cls.profile = Profile(
            name="synthetic",
            width=96,
            height=160,
            aspect_ratio=0.6,
            max_freeze=0.2,
            max_black=0.2,
            max_silence=0.2,
            target_lufs=-22,
            lufs_tolerance=4,
        )
        cls.media = MediaInfo(96, 160, 30, 3, True, 3, 3, audio_streams=1)

    def generate(self, path, video="testsrc=size=96x160:rate=30", audio="sine=frequency=440"):
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
                video,
                "-f",
                "lavfi",
                "-i",
                audio,
                "-t",
                "3",
                "-c:v",
                "ffv1",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "pcm_s16le",
                str(path),
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )

    def test_real_filters_accept_testsrc_sine_and_reject_frozen_black_silence(self):
        with temporary_directory() as directory:
            good = Path(directory) / "good.mkv"
            self.generate(good)
            result = measure(good, self.media, self.profile, self.ffmpeg, timeout=30)
            report = evaluate(str(good), self.media, result, self.profile)
            self.assertTrue(report.passed, report.checks)
            self.assertEqual(report.warnings, 0)
            self.assertEqual(result.freezes, [])
            self.assertEqual(result.black, [])
            self.assertEqual(result.silence, [])

            bad = Path(directory) / "bad.mkv"
            self.generate(bad, "color=c=black:size=96x160:rate=30", "anullsrc=r=44100:cl=mono")
            result = measure(bad, self.media, self.profile, self.ffmpeg, timeout=30)
            report = evaluate(str(bad), self.media, result, self.profile)
            failures = {c.name for c in report.checks if c.status == "fail"}
            self.assertTrue({"freeze", "black", "silence"} <= failures, report.checks)

    def test_real_filters_detect_clipped_original_audio(self):
        with temporary_directory() as directory:
            path = Path(directory) / "clipped.mkv"
            self.generate(path, audio="sine=frequency=440,volume=10")
            result = measure(path, self.media, self.profile, self.ffmpeg, timeout=30)
            self.assertGreaterEqual(result.sample_peak_dbfs, -0.01)
            report = evaluate(str(path), self.media, result, self.profile)
            self.assertIn("clipping", {c.name for c in report.checks if c.status == "fail"})

    @unittest.skipUnless(shutil.which("ffprobe"), "ffprobe not on PATH; filter tests still run")
    def test_end_to_end_with_ffprobe(self):
        with temporary_directory() as directory:
            path = Path(directory) / "tiny.mkv"
            self.generate(path)
            report = analyze(path, self.profile, ffmpeg=self.ffmpeg, timeout=30)
            self.assertTrue(report.passed, report.checks)
            self.assertEqual(report.probe_source, "ffprobe")

    def test_pipeline_clean_clip_passes(self):
        with temporary_directory() as directory:
            path = Path(directory) / "clean.mkv"
            self.generate(path)
            report = analyze(path, self.profile, ffmpeg=self.ffmpeg, timeout=30)
            self.assertTrue(report.passed, report.checks)
            self.assertEqual(report.failures, 0)

    def test_pipeline_black_segment_fails_black(self):
        with temporary_directory() as directory:
            path = Path(directory) / "black.mkv"
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
                    "testsrc=size=96x160:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:size=96x160:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440",
                    "-filter_complex",
                    "[0:v]trim=duration=1,setpts=PTS-STARTPTS[v0];"
                    "[1:v]trim=duration=2,setpts=PTS-STARTPTS[v1];"
                    "[v0][v1]concat=n=2:v=1:a=0[v]",
                    "-map",
                    "[v]",
                    "-map",
                    "2:a",
                    "-t",
                    "3",
                    "-c:v",
                    "ffv1",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "pcm_s16le",
                    str(path),
                ],
                capture_output=True,
                check=True,
                timeout=30,
            )
            report = analyze(path, self.profile, ffmpeg=self.ffmpeg, timeout=30)
            failures = {c.name for c in report.checks if c.status == "fail"}
            self.assertIn("black", failures, report.checks)

    def test_pipeline_frozen_section_fails_freeze(self):
        with temporary_directory() as directory:
            path = Path(directory) / "freeze.mkv"
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
                    "testsrc=size=96x160:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=blue:size=96x160:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440",
                    "-filter_complex",
                    "[0:v]trim=duration=1,setpts=PTS-STARTPTS[v0];"
                    "[1:v]trim=duration=2,setpts=PTS-STARTPTS[v1];"
                    "[v0][v1]concat=n=2:v=1:a=0[v]",
                    "-map",
                    "[v]",
                    "-map",
                    "2:a",
                    "-t",
                    "3",
                    "-c:v",
                    "ffv1",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "pcm_s16le",
                    str(path),
                ],
                capture_output=True,
                check=True,
                timeout=30,
            )
            report = analyze(path, self.profile, ffmpeg=self.ffmpeg, timeout=30)
            failures = {c.name for c in report.checks if c.status == "fail"}
            self.assertIn("freeze", failures, report.checks)

    def test_pipeline_silent_audio_fails_silence(self):
        with temporary_directory() as directory:
            path = Path(directory) / "silent.mkv"
            self.generate(path, audio="anullsrc=r=44100:cl=mono")
            report = analyze(path, self.profile, ffmpeg=self.ffmpeg, timeout=30)
            failures = {c.name for c in report.checks if c.status == "fail"}
            self.assertIn("silence", failures, report.checks)

    def test_pipeline_loud_clipped_sine_fails_peak(self):
        with temporary_directory() as directory:
            path = Path(directory) / "clipped.mkv"
            self.generate(path, audio="sine=frequency=440,volume=10")
            report = analyze(path, self.profile, ffmpeg=self.ffmpeg, timeout=30)
            failures = {c.name for c in report.checks if c.status == "fail"}
            self.assertTrue({"clipping", "true_peak"} & failures, report.checks)

    def test_pipeline_video_only_fails_require_audio(self):
        with temporary_directory() as directory:
            path = Path(directory) / "video_only.mkv"
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
                    "testsrc=size=96x160:rate=30",
                    "-t",
                    "3",
                    "-c:v",
                    "ffv1",
                    "-pix_fmt",
                    "yuv420p",
                    "-an",
                    str(path),
                ],
                capture_output=True,
                check=True,
                timeout=30,
            )
            report = analyze(path, self.profile, ffmpeg=self.ffmpeg, timeout=30)
            failures = {c.name for c in report.checks if c.status == "fail"}
            self.assertIn("audio", failures, report.checks)
