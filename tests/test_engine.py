import math
import unittest
from dataclasses import replace

from video_qa.engine import evaluate
from video_qa.models import Interval, Measurements, MediaInfo
from video_qa.profiles import Profile


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.profile = Profile()
        self.media = MediaInfo(1080, 1920, 30, 10, True, 10, 10, audio_streams=1)
        self.measured = Measurements(integrated_lufs=-14, true_peak_dbfs=-2, sample_peak_dbfs=-2)

    def report(self, media=None, measured=None, profile=None):
        return evaluate(
            "synthetic.mp4", media or self.media, measured or self.measured, profile or self.profile
        )

    def failures(self, report):
        return {c.name for c in report.checks if c.status == "fail"}

    def test_clean_input_passes(self):
        self.assertTrue(self.report().passed)
        self.assertEqual(self.report().warnings, 0)

    def test_each_metadata_rule_fails(self):
        for key, value, rule in (
            ("width", 720, "resolution"),
            ("fps", 23, "fps"),
            ("duration", 61, "duration"),
            ("height", 1080, "aspect_ratio"),
        ):
            with self.subTest(rule=rule):
                self.assertIn(
                    rule, self.failures(self.report(media=replace(self.media, **{key: value})))
                )

    def test_rotation_and_nonsquare_pixels(self):
        media = replace(self.media, width=1920, height=1080, rotation=90)
        self.assertTrue(self.report(media=media).passed)
        self.assertIn(
            "aspect_ratio",
            self.failures(self.report(media=replace(self.media, sample_aspect_ratio=2))),
        )

    def test_event_limit_is_per_contiguous_interval_with_inclusive_bounds(self):
        for attr, rule, limit in (
            ("freezes", "freeze", 1.5),
            ("black", "black", 0.5),
            ("silence", "silence", 2),
        ):
            with self.subTest(rule=rule):
                measured = replace(
                    self.measured, **{attr: [Interval(0, limit), Interval(3, 3 + limit)]}
                )
                self.assertTrue(self.report(measured=measured).passed)
                measured = replace(measured, **{attr: [Interval(0, limit + 0.05)]})
                self.assertIn(rule, self.failures(self.report(measured=measured)))

    def test_missing_audio_and_short_audio_fail(self):
        report = self.report(media=replace(self.media, has_audio=False))
        self.assertIn("audio", self.failures(report))
        self.assertNotIn("clipping", self.failures(report))
        self.assertIn(
            "audio_coverage",
            self.failures(self.report(media=replace(self.media, audio_duration=3))),
        )
        self.assertTrue(
            self.report(
                media=replace(self.media, has_audio=False),
                profile=replace(self.profile, require_audio=False),
            ).passed
        )

    def test_clipping_and_true_peak_are_independent(self):
        self.assertEqual(
            self.failures(self.report(measured=replace(self.measured, sample_peak_dbfs=0))),
            {"clipping"},
        )
        self.assertEqual(
            self.failures(self.report(measured=replace(self.measured, true_peak_dbfs=0.5))),
            {"true_peak"},
        )

    def test_missing_measurements_cannot_pass(self):
        self.assertIn("clipping", self.failures(self.report(measured=Measurements())))
        self.assertIn("true_peak", self.failures(self.report(measured=Measurements())))

    def test_loudness_warns_by_default_can_fail(self):
        measured = replace(self.measured, integrated_lufs=-25)
        report = self.report(measured=measured)
        self.assertTrue(report.passed)
        self.assertEqual(report.warnings, 1)
        self.assertIn(
            "loudness",
            self.failures(
                self.report(
                    measured=measured, profile=replace(self.profile, loudness_severity="fail")
                )
            ),
        )

    def test_silent_audio_has_valid_negative_infinity_but_silence_fails(self):
        measured = Measurements(
            silence=[Interval(0, 10)],
            integrated_lufs=-math.inf,
            true_peak_dbfs=-math.inf,
            sample_peak_dbfs=-math.inf,
        )
        self.assertEqual(self.failures(self.report(measured=measured)), {"silence"})

    def test_extra_streams_warn(self):
        report = self.report(media=replace(self.media, audio_streams=2))
        self.assertTrue(report.passed)
        self.assertEqual(report.warnings, 1)
