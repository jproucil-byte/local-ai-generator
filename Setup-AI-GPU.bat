@echo off
cd /d "%~dp0"
rem NVIDIA GPU: installs the PyTorch CUDA build that matches the installed driver.
python setup_ai.py --backend cuda
pause
