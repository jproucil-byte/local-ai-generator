"""Install AI extras into the same isolated environment as start.py."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv


def main():
    parser = argparse.ArgumentParser(description="Install Local Ai Generator engine. Requires internet and several GB free disk space.")
    parser.add_argument("--backend", choices=["cpu", "default", "existing"], default="cpu", help="cpu: portable baseline; default: PyPI torch build; existing: preserve an already installed ROCm/CUDA/XPU build")
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        raise SystemExit("Use Python 3.10–3.12.")
    root = Path(__file__).resolve().parent
    env = root / ".venv"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    def run(*arguments):
        subprocess.run([str(python), "-m", "pip", *arguments], check=True)
    if args.backend == "cpu" and sys.platform != "darwin":
        run("install", "torch>=2.5,<3", "--index-url", "https://download.pytorch.org/whl/cpu")
    elif args.backend == "default" or sys.platform == "darwin" and args.backend != "existing":
        run("install", "torch>=2.5,<3")
    else:
        subprocess.run([str(python), "-c", "import torch; print(torch.__version__)"], check=True)
    run("install", "-e", str(root) + "[ai]")
    subprocess.run([str(python), "-m", "localaigenerator.worker", "hardware"], cwd=root, check=True)
    print("AI engine ready. Run start.py / Start.bat / Start.command.")


if __name__ == "__main__":
    main()
