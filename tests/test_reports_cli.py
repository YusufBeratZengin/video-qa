import contextlib
import io
import json
import math
import subprocess
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from tests.support import temporary_directory
from video_qa.analyzer import AnalysisError, _run, analyze, find_ffmpeg, find_ffprobe
from video_qa.cli import main
from video_qa.models import Check, Measurements, Report
from video_qa.profiles import Profile
from video_qa.reports import human_report, json_report, junit_report


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.report = Report(
            'a<&".mp4',
            "shorts",
            [
                Check("resolution", "pass", "good"),
                Check("silence", "fail", "3s > 2s"),
                Check("loudness", "warn", "quiet < target"),
            ],
            measurements=Measurements(integrated_lufs=-math.inf),
        )

    def test_json_is_strict_and_keeps_warnings_separate(self):
        data = json.loads(json_report(self.report), parse_constant=lambda s: self.fail(s))
        self.assertFalse(data["passed"])
        self.assertEqual((data["failures"], data["warnings"]), (1, 1))
        self.assertEqual(data["measurements"]["integrated_lufs"], "-inf")

    def test_xml_is_parseable_escaped_and_counted(self):
        suite = ET.fromstring(junit_report(self.report))
        self.assertEqual(suite.attrib["tests"], "3")
        self.assertEqual(suite.attrib["failures"], "1")
        self.assertEqual(len(suite.findall("testcase/failure")), 1)
        self.assertEqual(len(suite.findall("testcase/system-out")), 1)
        self.assertEqual(suite.find("properties/property").attrib["value"], self.report.path)

    def test_xml_invalid_controls_are_sanitized(self):
        ET.fromstring(junit_report(Report("bad\x01file", "test", [Check("x", "fail", "\x00")])))

    def test_human_table(self):
        text = human_report(self.report)
        self.assertIn("WARN", text)
        self.assertIn("FAIL: 1 failure(s), 1 warning(s)", text)


class CliTests(unittest.TestCase):
    def invoke(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(args)
        return result, stdout.getvalue(), stderr.getvalue()

    @patch("video_qa.cli.analyze")
    def test_warn_is_exit_zero_and_overrides_are_applied(self, analyze_mock):
        analyze_mock.return_value = Report("out.mp4", "shorts", [Check("loudness", "warn", "low")])
        code, output, _ = self.invoke(
            ["check", "out.mp4", "--format", "json", "--max-freeze", "0.2", "--target-lufs", "-16"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["warnings"], 1)
        profile = analyze_mock.call_args.args[1]
        self.assertEqual(profile.max_freeze, 0.2)
        self.assertEqual(profile.target_lufs, -16)

    @patch("video_qa.cli.analyze")
    def test_fail_on_warn_exits_one(self, analyze_mock):
        analyze_mock.return_value = Report("out.mp4", "shorts", [Check("loudness", "warn", "low")])
        code, _, _ = self.invoke(["check", "out.mp4", "--fail-on-warn"])
        self.assertEqual(code, 1)

    def test_list_profiles_flag(self):
        for args in (["--list-profiles"], ["check", "--list-profiles"]):
            with self.subTest(args=args):
                code, stdout, _ = self.invoke(args)
                self.assertEqual(code, 0)
                self.assertIn("shorts", stdout)
                self.assertIn("reels", stdout)
                self.assertIn("tiktok", stdout)
                self.assertIn("1080x1920", stdout)

    @patch("video_qa.cli.analyze", side_effect=AnalysisError("ffprobe not found"))
    def test_operational_failure_is_machine_readable_and_exit_one(self, _):
        code, output, _ = self.invoke(["check", "out.mp4", "--format", "json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)["checks"][0]["name"], "analysis")
        self.assertIn("ffprobe", output)

    @patch("video_qa.cli.analyze")
    def test_junit_file_and_failed_gate(self, analyze_mock):
        analyze_mock.return_value = Report("out.mp4", "shorts", [Check("freeze", "fail", "bad")])
        with temporary_directory() as directory:
            output = Path(directory) / "junit.xml"
            code, stdout, _ = self.invoke(
                ["check", "out.mp4", "--format", "junit", "--output", str(output)]
            )
            self.assertEqual(code, 1)
            self.assertEqual(stdout, "")
            self.assertEqual(ET.fromstring(output.read_text()).attrib["failures"], "1")

    def test_invalid_options_and_config_exit_two(self):
        for args in (
            ["--max-freeze", "-1"],
            ["--max-duration", "nan"],
            ["--timeout", "0"],
            ["--profile", "unknown"],
            ["--output", "out.mp4"],
        ):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["check", "out.mp4", *args])
                self.assertEqual(raised.exception.code, 2)

    def test_missing_file_fails_without_traceback(self):
        code, output, _ = self.invoke(["check", "does-not-exist.mp4"])
        self.assertEqual(code, 1)
        self.assertIn("not a regular file", output)


class ProcessTests(unittest.TestCase):
    def test_explicit_binaries_and_missing_probe(self):
        self.assertEqual(find_ffmpeg("custom-ffmpeg"), "custom-ffmpeg")
        self.assertEqual(find_ffprobe("custom-ffprobe"), "custom-ffprobe")
        with patch("video_qa.analyzer.shutil.which", return_value=None):
            with self.assertRaisesRegex(AnalysisError, "supplies only ffmpeg"):
                find_ffprobe()

    @patch("video_qa.analyzer.subprocess.run")
    def test_timeout_nonzero_and_missing_executable(self, run):
        for error in (subprocess.TimeoutExpired("ffmpeg", 1), FileNotFoundError("missing")):
            run.side_effect = error
            with self.assertRaises(AnalysisError):
                _run(["ffmpeg", "-version"], 1)
        run.side_effect = None
        run.return_value = subprocess.CompletedProcess(["ffmpeg"], 1, "", "decoder error")
        with self.assertRaisesRegex(AnalysisError, "decoder error"):
            _run(["ffmpeg"], 1)
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs["env"]["LC_ALL"], "C")

    @patch("video_qa.analyzer.measure")
    @patch("video_qa.analyzer.probe")
    def test_full_pipeline_connects_probe_measurements_and_rules(self, probe_mock, measure_mock):
        from video_qa.parsers import parse_probe

        fixture = Path(__file__).parent / "fixtures" / "probe.json"
        probe_mock.return_value = parse_probe(fixture.read_text())
        measure_mock.return_value = Measurements(
            integrated_lufs=-14, true_peak_dbfs=-2, sample_peak_dbfs=-2
        )
        with temporary_directory() as directory:
            path = Path(directory) / "input.mkv"
            path.touch()
            report = analyze(path, Profile(), ffmpeg="ffmpeg", ffprobe="ffprobe")
        self.assertTrue(report.passed)
