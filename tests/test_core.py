import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from localaigenerator.core import Request, data_root, load_settings, save_settings, select_device


def fake_torch(cuda=False, mps=False, xpu=False):
    return SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: cuda), backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)), xpu=SimpleNamespace(is_available=lambda: xpu))


class CoreTests(unittest.TestCase):
    def test_rename_reuses_existing_linux_data(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"XDG_DATA_HOME": folder}, clear=True), patch("localaigenerator.core.platform.system", return_value="Linux"):
            legacy = Path(folder) / "local-ai-generator"
            legacy.mkdir()
            self.assertEqual(data_root(), legacy)

    def test_windows_data_root_does_not_need_home_directory(self):
        # CI regression: with a cleared environment Path.home() raises on Windows.
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAPPDATA": folder}, clear=True), patch("localaigenerator.core.platform.system", return_value="Windows"), patch.object(Path, "home", side_effect=RuntimeError("no home")):
            self.assertEqual(data_root(), Path(folder) / "LocalAiGenerator")

    def test_old_environment_override_still_supported(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAIGENERATOR_HOME": folder}, clear=True):
            self.assertEqual(data_root(), Path(folder))

    def test_device_priority_and_cpu_fallback(self):
        for flags, expected in [((True, True, True), "cuda"), ((False, True, True), "mps"), ((False, False, True), "xpu"), ((False, False, False), "cpu")]:
            self.assertEqual(select_device(fake_torch(*flags)), expected)

    def test_explicit_unavailable_device_is_rejected(self):
        with self.assertRaises(ValueError):
            select_device(fake_torch(), "cuda")

    def test_missing_backend_attributes(self):
        torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False), backends=SimpleNamespace())
        self.assertEqual(select_device(torch), "cpu")

    def test_image_request(self):
        self.assertEqual(Request("sd15", "lake", "outputs").validate().width, 512)

    def test_invalid_prompt_dimensions_and_seed(self):
        for kwargs in ({"prompt": " "}, {"width": 513}, {"seed": -2}, {"guidance": 31}, {"steps": 0}):
            values = {"model": "sd15", "prompt": "lake", "output": "outputs", **kwargs}
            with self.assertRaises(ValueError):
                Request(**values).validate()

    def test_turbo_cannot_use_generic_settings(self):
        with self.assertRaises(ValueError):
            Request("turbo", "lake", "outputs").validate()
        Request("turbo", "lake", "outputs", steps=4, guidance=0).validate()

    def test_video_temporal_and_spatial_constraints(self):
        Request("ltx", "lake", "outputs", frames=25, width=512, height=320).validate()
        for kwargs in ({"frames": 24}, {"width": 520}, {"fps": 0}):
            with self.assertRaises(ValueError):
                Request("ltx", "lake", "outputs", **kwargs).validate()

    def test_audio_duration(self):
        with self.assertRaises(ValueError):
            Request("audioldm2", "rain", "outputs", seconds=11).validate()

    def test_settings_corruption_and_atomic_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAIGENERATOR_HOME": folder}):
            self.assertEqual(load_settings(), {})
            save_settings({"output": "folder-\u017e\u0165\u010d"})
            self.assertEqual(load_settings()["output"], "folder-\u017e\u0165\u010d")
            (Path(folder) / "settings.json").write_text("broken")
            self.assertEqual(load_settings(), {})


if __name__ == "__main__":
    unittest.main()
