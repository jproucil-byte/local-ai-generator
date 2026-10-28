"""Install AI extras into the same isolated environment as start.py."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import venv

TORCH = "torch>=2.5,<3"
TORCH_INDEX = "https://download.pytorch.org/whl/"
# Newest first: (lowest CUDA version the NVIDIA driver must support, PyTorch wheel index).
CUDA_BUILDS = (((13, 0), "cu130"), ((12, 8), "cu128"), ((12, 6), "cu126"))


def pick_cuda_build(nvidia_smi_output):
    """Newest PyTorch CUDA build the installed NVIDIA driver can run, or None."""
    match = re.search(r"CUDA Version:\s*(\d+)\.(\d+)", nvidia_smi_output or "")
    if not match:
        return None
    version = (int(match.group(1)), int(match.group(2)))
    return next((name for minimum, name in CUDA_BUILDS if version >= minimum), None)


def torch_install_args(backend, platform, cuda_build=None):
    """pip arguments that install PyTorch for the backend, or None to keep what is installed."""
    if backend == "existing":
        return None
    if backend == "cuda":
        if platform == "darwin":
            raise ValueError("CUDA is not available on macOS. Use --backend cpu.")
        if not cuda_build:
            raise ValueError("No CUDA build selected.")
        return [TORCH, "--index-url", TORCH_INDEX + cuda_build]
    if backend == "cpu" and platform != "darwin":
        return [TORCH, "--index-url", TORCH_INDEX + "cpu"]
    return [TORCH]


def nvidia_smi_output():
    """Text printed by nvidia-smi, or None when no NVIDIA driver is installed."""
    candidates = [shutil.which("nvidia-smi")]
    if os.name == "nt":
        candidates.append(str(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe"))
    for executable in candidates:
        if executable and Path(executable).is_file():
            try:
                return subprocess.run([executable], capture_output=True, text=True, timeout=30).stdout
            except (OSError, subprocess.SubprocessError):
                continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Install Local Ai Generator engine. Requires internet and several GB free disk space.")
    parser.add_argument("--backend", choices=["cpu", "default", "cuda", "existing"], default="cpu", help="cpu: portable baseline; cuda: NVIDIA GPU build chosen from the installed driver (Windows/Linux); default: PyPI torch build (CPU-only on Windows); existing: preserve an already installed ROCm/CUDA/XPU build")
    parser.add_argument("--cuda-build", choices=[name for _, name in CUDA_BUILDS], help="with --backend cuda: force a PyTorch CUDA build instead of detecting it from the NVIDIA driver")
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        raise SystemExit("Use Python 3.10–3.12.")
    cuda_build = None
    if args.backend == "cuda":
        if sys.platform == "darwin":
            raise SystemExit("CUDA is not available on macOS. Use --backend cpu.")
        cuda_build = args.cuda_build
        if not cuda_build:
            output = nvidia_smi_output()
            if output is None:
                raise SystemExit("No NVIDIA driver found (nvidia-smi is missing). Install the NVIDIA driver, or use the CPU setup.")
            cuda_build = pick_cuda_build(output)
            if not cuda_build:
                raise SystemExit("The NVIDIA driver is too old for current PyTorch CUDA builds (CUDA 12.6 or newer is required). Update the driver, or use the CPU setup.")
        print("Selected PyTorch build:", cuda_build)
    root = Path(__file__).resolve().parent
    env = root / ".venv"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(env)

    def run(*arguments):
        subprocess.run([str(python), "-m", "pip", *arguments], check=True)

    keep_installed_torch = False
    if args.backend == "cuda":
        # A CPU-only torch already in the environment satisfies the version range, so pip would keep it.
        probe = subprocess.run([str(python), "-c", "import torch; print(torch.version.cuda or '')"], capture_output=True, text=True)
        if probe.returncode == 0 and not probe.stdout.strip():
            run("uninstall", "-y", "torch")
        elif probe.returncode == 0:
            keep_installed_torch = True
            print("A CUDA build of PyTorch is already installed; keeping it.")
    torch_args = torch_install_args(args.backend, sys.platform, cuda_build)
    if torch_args and not keep_installed_torch:
        run("install", *torch_args)
    elif torch_args is None:
        subprocess.run([str(python), "-c", "import torch; print(torch.__version__)"], check=True)
    run("install", "-e", str(root) + "[ai]")
    subprocess.run([str(python), "-m", "localaigenerator.worker", "hardware"], cwd=root, check=True)
    if args.backend == "cuda":
        ready = subprocess.run([str(python), "-c", "import sys, torch; sys.exit(0 if torch.cuda.is_available() else 1)"]).returncode == 0
        if not ready:
            print("WARNING: PyTorch cannot use the NVIDIA GPU, so generation would run on the CPU. Update the NVIDIA driver and run this setup again.")
    print("AI engine ready. Run start.py / Start.bat / Start.command.")


if __name__ == "__main__":
    main()
