from pathlib import Path
import unittest
import setup_ai

ROOT = Path(__file__).resolve().parent.parent


def smi(cuda):
    return f"| NVIDIA-SMI 576.02   Driver Version: 576.02   CUDA Version: {cuda} |\n| NVIDIA GeForce RTX 4060 Laptop GPU |"


class SetupTests(unittest.TestCase):
    def test_cuda_build_follows_the_driver(self):
        for reported, expected in [("13.0", "cu130"), ("13.1", "cu130"), ("12.9", "cu128"), ("12.8", "cu128"), ("12.7", "cu126"), ("12.6", "cu126"), ("12.4", None), ("11.8", None)]:
            self.assertEqual(setup_ai.pick_cuda_build(smi(reported)), expected, reported)

    def test_unreadable_nvidia_smi_output_selects_nothing(self):
        for text in ("", None, "NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver."):
            self.assertIsNone(setup_ai.pick_cuda_build(text))

    def test_torch_install_arguments(self):
        torch = setup_ai.TORCH
        self.assertEqual(setup_ai.torch_install_args("cpu", "win32"), [torch, "--index-url", "https://download.pytorch.org/whl/cpu"])
        self.assertEqual(setup_ai.torch_install_args("cuda", "win32", "cu128"), [torch, "--index-url", "https://download.pytorch.org/whl/cu128"])
        self.assertEqual(setup_ai.torch_install_args("cuda", "linux", "cu126"), [torch, "--index-url", "https://download.pytorch.org/whl/cu126"])
        self.assertEqual(setup_ai.torch_install_args("default", "win32"), [torch])
        self.assertEqual(setup_ai.torch_install_args("cpu", "darwin"), [torch])
        self.assertIsNone(setup_ai.torch_install_args("existing", "win32"))

    def test_cuda_is_rejected_on_macos_and_without_a_build(self):
        with self.assertRaises(ValueError):
            setup_ai.torch_install_args("cuda", "darwin", "cu128")
        with self.assertRaises(ValueError):
            setup_ai.torch_install_args("cuda", "win32")

    def test_windows_gpu_launcher_installs_the_cuda_build(self):
        # The PyPI build of PyTorch is CPU-only on Windows, which silently disabled the GPU.
        self.assertIn("--backend cuda", (ROOT / "Setup-AI-GPU.bat").read_text())


if __name__ == "__main__":
    unittest.main()
