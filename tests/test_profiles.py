import json
import unittest
from dataclasses import replace
from pathlib import Path

from tests.support import temporary_directory
from video_qa.profiles import BUILTINS, Profile, load_profile


class ProfileTests(unittest.TestCase):
    def test_builtins(self):
        for name, duration in (("shorts", 60), ("reels", 90), ("tiktok", 180)):
            profile = load_profile(name)
            self.assertEqual(profile.name, name)
            self.assertEqual(profile.max_duration, duration)
            self.assertEqual((profile.width, profile.height), (1080, 1920))

    def test_json_toml_and_inheritance(self):
        with temporary_directory() as directory:
            root = Path(directory)
            json_path = root / "custom.json"
            json_path.write_text(
                json.dumps({"extends": "reels", "max_freeze": 0.25}), encoding="utf-8-sig"
            )
            profile = load_profile(str(json_path))
            self.assertEqual(profile.max_duration, 90)
            self.assertEqual(profile.max_freeze, 0.25)
            self.assertEqual(profile.name, "custom")
            toml_path = root / "custom.toml"
            toml_path.write_text(
                'extends = "tiktok"\nmax_duration = 120\nrequire_audio = false\n', encoding="utf-8"
            )
            profile = load_profile(str(toml_path))
            self.assertFalse(profile.require_audio)
            self.assertEqual(profile.max_duration, 120)
            self.assertEqual(BUILTINS["tiktok"].max_duration, 180)

    def test_invalid_config(self):
        with temporary_directory() as directory:
            path = Path(directory) / "bad.json"
            for data in (
                [1],
                {"max_frezze": 1},
                {"extends": "missing"},
                {"extends": []},
                {"width": "1080"},
                {"max_freeze": -1},
                {"require_audio": "false"},
                {"loudness_severity": []},
            ):
                with self.subTest(data=data), self.assertRaises(ValueError):
                    path.write_text(json.dumps(data), encoding="utf-8")
                    load_profile(str(path))

    def test_bounds_and_types(self):
        cases = {
            "max_freeze": -1,
            "max_black": float("nan"),
            "target_lufs": -100,
            "width": True,
            "height": 1.5,
            "max_fps": 23,
            "max_duration": 0.01,
            "silence_db": 1,
            "black_picture_ratio": 2,
            "loudness_severity": "ignore",
            "max_silence": float("inf"),
            "name": "",
            "aspect_ratio": 0,
        }
        for key, value in cases.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                replace(Profile(), **{key: value})
