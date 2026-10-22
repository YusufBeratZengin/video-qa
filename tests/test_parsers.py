import json
import math
import unittest
from pathlib import Path

from video_qa.models import Interval
from video_qa.parsers import (
    ParseError,
    parse_astats,
    parse_ffmpeg_info,
    parse_intervals,
    parse_loudnorm,
    parse_probe,
)

FIXTURES = Path(__file__).parent / "fixtures"


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((FIXTURES / "probe.json").read_text())

    def parse(self):
        return parse_probe(json.dumps(self.data))

    def test_rational_fps_and_stream_selection(self):
        media = self.parse()
        self.assertAlmostEqual(media.fps, 29.97002997)
        self.assertEqual((media.width, media.height), (1080, 1920))
        self.assertTrue(media.has_audio)
        self.assertEqual(media.duration, 4)

    def test_ignores_cover_and_counts_playable_streams(self):
        self.data["streams"].insert(
            0, {"codec_type": "video", "width": 20, "disposition": {"attached_pic": 1}}
        )
        self.assertEqual(self.parse().video_streams, 1)
        self.assertEqual(self.parse().width, 1080)

    def test_rotation_sar_and_fallbacks(self):
        video = self.data["streams"][0]
        video.update(
            width=1920,
            height=1080,
            avg_frame_rate="0/0",
            sample_aspect_ratio="2:1",
            side_data_list=[{"rotation": -90}],
        )
        del video["duration"]
        media = self.parse()
        self.assertEqual(media.fps, 30)
        self.assertAlmostEqual(media.display_aspect_ratio, 1080 / 3840)
        self.assertEqual(media.video_duration, 4)

    def test_long_audio_cannot_hide_behind_video_duration(self):
        self.data["streams"][1]["duration"] = "90"
        self.assertEqual(self.parse().duration, 90)

    def test_missing_audio_is_valid(self):
        self.data["streams"] = self.data["streams"][:1]
        self.assertFalse(self.parse().has_audio)
        self.assertIsNone(self.parse().audio_duration)

    def test_bad_probe_data_fails_closed(self):
        for text in ("garbage", "[]", "{}", '{"streams": []}', '{"streams": null}'):
            with self.subTest(text=text), self.assertRaises(ParseError):
                parse_probe(text)
        for key, value in (
            ("width", 0),
            ("height", -1),
            ("duration", "nan"),
            ("avg_frame_rate", "0/0"),
        ):
            with self.subTest(key=key):
                original = dict(self.data["streams"][0])
                self.data["streams"][0][key] = value
                if key == "duration":
                    self.data["format"]["duration"] = "N/A"
                if key == "avg_frame_rate":
                    self.data["streams"][0]["r_frame_rate"] = "0/0"
                with self.assertRaises(ParseError):
                    self.parse()
                self.data["streams"][0] = original


class FilterTests(unittest.TestCase):
    def test_captured_freeze_and_black(self):
        text = (FIXTURES / "video.log").read_text()
        freeze = parse_intervals(text, "freeze", 3)
        black = parse_intervals(text, "black", 3)
        self.assertEqual(len(freeze), 1)
        self.assertGreater(freeze[0].duration, 2.8)
        self.assertEqual(len(black), 1)
        self.assertGreater(black[0].duration, 2.8)

    def test_captured_silent_audio(self):
        text = (FIXTURES / "silence.log").read_text()
        silence = parse_intervals(text, "silence", 3)
        self.assertEqual(len(silence), 1)
        self.assertAlmostEqual(silence[0].duration, 3, places=2)
        self.assertEqual(parse_loudnorm(text), (-math.inf, -math.inf))
        self.assertEqual(parse_astats(text), -math.inf)

    def test_captured_sine_uses_input_loudness_and_original_peaks(self):
        text = (FIXTURES / "audio.log").read_text()
        lufs, peak = parse_loudnorm(text)
        self.assertTrue(-25 < lufs < -18)
        self.assertTrue(-20 < peak < -16)
        self.assertTrue(-20 < parse_astats(text) < -16)
        self.assertEqual(parse_intervals(text, "silence", 3), [])

    def test_log_variations_and_open_eof_interval(self):
        text = (
            "[Parsed_freezedetect @ 0x1] lavfi.freezedetect.freeze_start: 1e-1\r\n"
            "[different prefix] freeze_duration: 1 freeze_end: 1.1\r\n"
            "freeze_start: 2.0\r\n"
        )
        self.assertEqual(parse_intervals(text, "freeze", 4), [Interval(0.1, 1.1), Interval(2, 4)])
        self.assertEqual(parse_intervals("silence_start: -0.01", "silence", 2), [Interval(0, 2)])
        self.assertEqual(
            parse_intervals("black_start: 1 black_end: 2", "black", 4), [Interval(1, 2)]
        )
        self.assertEqual(parse_intervals("silence_end: 4", "silence", 4), [])

    def test_empty_log_does_not_invent_events(self):
        self.assertEqual(parse_intervals("unrelated diagnostics", "freeze", 3), [])

    def test_reversed_event_is_error(self):
        with self.assertRaises(ParseError):
            parse_intervals("freeze_start: 2 freeze_end: 1", "freeze", 3)

    def test_loudnorm_skips_unrelated_braces_and_accepts_number_types(self):
        self.assertEqual(
            parse_loudnorm('noise {oops} {"other": 1}\n{"input_i": -14, "input_tp": "-1.1"}'),
            (-14, -1.1),
        )

    def test_peak_is_highest_across_channels(self):
        self.assertEqual(
            parse_astats("Peak level dB: -2\r\nPeak level dB: -0.01\nPeak level dB: -1"), -0.01
        )

    def test_missing_or_nonfinite_required_measurements_raise(self):
        for text in (
            "",
            '{"output_i": "-14"}',
            '{"input_i":"nan","input_tp":"-1"}',
            '{"input_i":"-14","input_tp":"inf"}',
        ):
            with self.subTest(text=text), self.assertRaises(ParseError):
                parse_loudnorm(text)
        for text in ("no peaks", "Peak level dB: nan", "Peak level dB: +inf"):
            with self.subTest(text=text), self.assertRaises(ParseError):
                parse_astats(text)

    def test_silence_trailing_quirk_ignored(self):
        text = (FIXTURES / "silence_trailing.log").read_text()
        # Stream duration is 3.0, trailing silence begins at 3.001 and ends at 3.018.
        # Intervals with start >= stream duration or 0 length must be ignored.
        silence = parse_intervals(text, "silence", 3.0)
        self.assertEqual(silence, [])


class FFmpegInfoTests(unittest.TestCase):
    def test_captured_h264_aac(self):
        text = (FIXTURES / "ffmpeg_h264_aac.log").read_text()
        media = parse_ffmpeg_info(text)
        self.assertEqual((media.width, media.height), (1080, 1920))
        self.assertAlmostEqual(media.fps, 30.0)
        self.assertAlmostEqual(media.duration, 4.0)
        self.assertTrue(media.has_audio)
        self.assertEqual(media.video_streams, 1)
        self.assertEqual(media.audio_streams, 1)
        self.assertEqual(media.rotation, 0)
        self.assertAlmostEqual(media.sample_aspect_ratio, 1.0)

    def test_captured_video_only(self):
        text = (FIXTURES / "ffmpeg_video_only.log").read_text()
        media = parse_ffmpeg_info(text)
        self.assertEqual((media.width, media.height), (1080, 1920))
        self.assertFalse(media.has_audio)
        self.assertIsNone(media.audio_duration)
        self.assertEqual(media.audio_streams, 0)

    def test_captured_audio_only_raises(self):
        text = (FIXTURES / "ffmpeg_audio_only.log").read_text()
        with self.assertRaisesRegex(ParseError, "No playable video stream found"):
            parse_ffmpeg_info(text)

    def test_rotation_sar_and_cover(self):
        text = (
            "Input #0, matroska,webm, from 'test.mkv':\n"
            "  Duration: 00:00:05.00, start: 0.000000, bitrate: 500 kb/s\n"
            "  Stream #0:0: Video: mjpeg, 500x500 (attached pic)\n"
            "  Stream #0:1: Video: h264, 1920x1080 [SAR 2:1 DAR 32:9], 25 fps, 25 tbr\n"
            "    Side data:\n"
            "      displaymatrix: rotation of -90.00 degrees\n"
            "  Stream #0:2: Audio: aac, 48000 Hz, stereo\n"
        )
        media = parse_ffmpeg_info(text)
        self.assertEqual((media.width, media.height), (1920, 1080))
        self.assertEqual(media.video_streams, 1)
        self.assertEqual(media.rotation, -90)
        self.assertAlmostEqual(media.sample_aspect_ratio, 2.0)
        self.assertAlmostEqual(media.fps, 25.0)

    def test_bad_ffmpeg_info_fails_closed(self):
        for text in (
            "unrelated output",
            "Duration: N/A\nStream #0:0: Video: h264, 1080x1920, 30 fps",
            "Duration: 00:00:01.00\nStream #0:0: Video: h264, 1080x1920, 0 fps",
            "Duration: 00:00:01.00\nStream #0:0: Video: h264, 0x0, 30 fps",
        ):
            with self.subTest(text=text), self.assertRaises(ParseError):
                parse_ffmpeg_info(text)

        rot_text = (
            "Duration: 00:00:01.00\n"
            "Stream #0:0: Video: h264, 1080x1920, 30 fps\n"
            "  Side data:\n"
            "    displaymatrix: rotation of 45.00 degrees\n"
        )
        with self.assertRaisesRegex(ParseError, "Only right-angle display rotation is supported"):
            parse_ffmpeg_info(rot_text)
