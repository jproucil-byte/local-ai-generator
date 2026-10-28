from contextlib import nullcontext
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from localaigenerator.core import Request
from localaigenerator import worker


class WorkerTests(unittest.TestCase):
    def test_events_survive_non_utf8_console_encodings(self):
        # The GUI parses the worker's stdout as UTF-8 JSON. Windows pipes use the system code page,
        # so events with diacritics or an ellipsis must stay pure ASCII to arrive intact.
        code = "from localaigenerator import worker; worker.emit('status', text='Loading\\u2026'); worker.emit('done', path='C:\\\\Users\\\\Ji\\u0159\\u00ed\\\\creation.png', seed=7)"
        root = Path(__file__).resolve().parent.parent
        for encoding in ("cp1250", "cp437", "utf-8"):
            with self.subTest(encoding=encoding):
                result = subprocess.run([sys.executable, "-c", code], cwd=root, env={**os.environ, "PYTHONIOENCODING": encoding}, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
                events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
                self.assertEqual([event["event"] for event in events], ["status", "done"])
                self.assertEqual(events[0]["text"], "Loading\u2026")
                self.assertEqual(events[1]["path"], "C:\\Users\\Ji\u0159\u00ed\\creation.png")

    def run_model(self, key):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source"
            source.mkdir()
            (source / "model_index.json").write_text("{}")
            image = Mock()
            image.save.side_effect = lambda path, **kwargs: Path(path).write_bytes(b"PNG")
            pipe = Mock()
            pipe.return_value = SimpleNamespace(images=[image], audios=[[0.0]], frames=[["frame"]], nsfw_content_detected=None)
            factory = Mock()
            factory.from_pretrained.return_value = pipe
            torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False), backends=SimpleNamespace(), float32="float32", Generator=lambda **kwargs: SimpleNamespace(manual_seed=lambda seed: "generator"), inference_mode=nullcontext)
            sf = SimpleNamespace(write=lambda path, audio, rate, **kwargs: Path(path).write_bytes(b"WAV"))
            utils = SimpleNamespace(export_to_video=lambda frames, path, **kwargs: Path(path).write_bytes(b"MP4"))
            model = worker.get_model(key)
            request = Request(key, "test", folder, local_model=str(source), width=model.width, height=model.height, steps=model.steps, guidance=model.guidance, seed=42)
            modules = {"torch": torch, "diffusers": SimpleNamespace(**{model.pipeline: factory}), "soundfile": sf, "diffusers.utils": utils}
            events = []
            with patch.dict(sys.modules, modules), patch.dict(os.environ, {}, clear=False), patch.object(worker, "emit", lambda event, **kwargs: events.append({"event": event, **kwargs})):
                worker.generate(request)
                self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
            factory.from_pretrained.assert_called_once()
            self.assertTrue(factory.from_pretrained.call_args.kwargs["local_files_only"])
            self.assertTrue(factory.from_pretrained.call_args.kwargs["use_safetensors"])
            done = events[-1]
            self.assertEqual(done["event"], "done")
            path = Path(done["path"])
            self.assertTrue(path.is_file())
            metadata = json.loads((path.parent / "creation.json").read_text())
            self.assertEqual(metadata["seed"], 42)
            self.assertEqual(metadata["resolved_device"], "cpu")
            if model.kind == "video":
                self.assertEqual(pipe.call_args.kwargs["frame_rate"], 24)
            return path.suffix

    def test_image_offline_export(self):
        self.assertEqual(self.run_model("sd15"), ".png")

    def test_video_offline_export(self):
        self.assertEqual(self.run_model("ltx"), ".mp4")

    def test_audio_offline_export(self):
        self.assertEqual(self.run_model("audioldm2"), ".wav")

    def test_incomplete_download_not_marked_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            hub = SimpleNamespace(snapshot_download=Mock(side_effect=RuntimeError("interrupted")))
            with patch.dict(sys.modules, {"huggingface_hub": hub}), patch.object(worker, "model_root", lambda: Path(folder)), patch.object(worker, "emit"):
                with self.assertRaises(RuntimeError):
                    worker.download("sd15")
            self.assertFalse((Path(folder) / "sd15" / ".localaigenerator-complete").exists())

    def test_download_only_component_weights_and_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            def snapshot(**kwargs):
                target = Path(kwargs["local_dir"])
                target.mkdir()
                (target / "model_index.json").write_text("{}")
                self.assertIn("*/*.safetensors", kwargs["allow_patterns"])
                self.assertNotIn("*.safetensors", kwargs["allow_patterns"])
            with patch.dict(sys.modules, {"huggingface_hub": SimpleNamespace(snapshot_download=snapshot)}), patch.object(worker, "model_root", lambda: Path(folder)), patch.object(worker, "emit"):
                worker.download("ltx")
            self.assertTrue((Path(folder) / "ltx" / ".localaigenerator-complete").exists())


if __name__ == "__main__":
    unittest.main()
