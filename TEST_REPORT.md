# Validation — 2026-10-06

Version: 0.1.0. Environment: Linux x86_64, Python 3.12.14.

## Passed

- 14 dependency-free unit tests: device selection and missing accelerators, request validation, video dimensions/frame counts, audio duration, settings corruption, offline loader/export protocol and interrupted download completion markers.
- Qt offscreen GUI smoke test: image/video/audio modes, real subprocess completion/error recovery, and cancellation of a running process. Tested both without the AI engine and with it installed.
- GUI visually inspected from a rendered screenshot; scrolling retains access to controls on smaller windows.
- Editable project installation with the `ai` extra in a fresh virtual environment containing a CPU PyTorch build.
- Imports of StableDiffusionPipeline, StableDiffusionXLPipeline, LTXPipeline and AudioLDM2Pipeline.
- Real CPU image inference through the application worker using Hugging Face's tiny Stable Diffusion test fixture, converted locally to safetensors: 256 × 256, two steps, seed 42; PNG and parameter JSON exported successfully. The tiny fixture is a functional test, not a useful image-quality model, and is not bundled.
- Real WAV and MP4 encoding with the installed libraries; no generated fixture media is bundled.
- Python compilation of the application and setup scripts.

## Not yet verified

- Full-size SD 1.5 / SDXL / SDXL Turbo image quality or memory consumption.
- Actual model inference with LTX Video or AudioLDM 2.
- Real GPU execution on NVIDIA, AMD ROCm, Intel XPU or Apple MPS.
- Installation/execution on Windows or macOS.
- GitHub Actions runs (workflow prepared; no new repository exists yet).
- Air-gapped installation on a separate machine.

The interface and CPU image path are functional; video/audio integration remains experimental pending full-model tests. Mocked export tests do not substitute for real model inference. Hardware compatibility depends on OS, PyTorch build, drivers, RAM and the selected model.

## Tested engine versions

- torch 2.14.1+cpu
- diffusers 0.36.0
- transformers 4.57.6
- accelerate 1.15.0
- huggingface-hub 0.36.2
- safetensors 0.8.0
- PySide6 6.8.3

These are the Linux test environment versions, not a cross-platform lockfile. The project uses bounded dependency ranges in `pyproject.toml`.

## Rename validation — 2026-10-08

Renamed UI, Python package, launchers, documentation and repository references to Local Ai Generator. All 16 unit tests and the Qt GUI smoke test passed. Added compatibility with existing LocalAiGenerator data directories, completion markers and environment overrides. Real model inference was not repeated for this branding change.
