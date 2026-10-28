"""Create an isolated GUI environment. AI engines are installed explicitly via setup_ai.py."""
import os
from pathlib import Path
import subprocess
import sys
import venv


def main():
    if not (3, 10) <= sys.version_info[:2] <= (3, 12):
        raise SystemExit("Install 64-bit Python 3.10–3.12 first.")
    root = Path(__file__).resolve().parent
    env = root / ".venv"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    marker = env / ".localaigenerator-gui-installed"
    if not marker.exists():
        subprocess.run([str(python), "-m", "pip", "install", "-e", str(root)], check=True)
        marker.write_text("0.1.0", encoding="utf-8")
    subprocess.run([str(python), "-m", "localaigenerator.gui"], cwd=root, check=True)


if __name__ == "__main__":
    main()
