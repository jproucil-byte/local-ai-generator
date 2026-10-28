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
- GitHub Actions results (workflow committed to the repository; remote run results have not been verified).
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

## English-only interface — 2026-10-09

Translated the complete interface, model descriptions, validation messages, worker status and errors, and README into English. Existing setup scripts and code comments were already English. Set English locale defaults and use Qt folder dialogs to avoid localized native system dialogs. Updated the interface screenshot. All 16 unit tests and the GUI smoke test passed. Model inference was not repeated for this language-only change. The copyright holder retains their original proper name.

## Windows fixes and desktop check — 2026-10-18

GitHub Actions failed on `windows-latest` / Python 3.10 (the Windows 3.12 and macOS 3.10 jobs were cancelled by fail-fast) because `data_root()` always evaluated `Path.home()`, which raises on Windows when the environment is cleared, as one unit test does. The home directory is now resolved only when it is actually needed. A new regression test covers this; whether the Windows jobs pass is confirmed by the Actions run, not by this report.

Found and fixed: the worker printed its JSON events with non-ASCII characters. The GUI reads the pipe as UTF-8, but Windows pipes use the system code page (cp1250 on a Czech system), so the status text containing "…" and any result path with diacritics (for example `C:\Users\Jiří\…`) were silently dropped, leaving the GUI without a confirmed result even though the image was saved. Events are now ASCII-only JSON. A new test runs the worker under cp1250, cp437 and UTF-8 and fails on the previous code.

Results: 18 unit tests pass (2 new) and the new tests fail on the previous code; Python compilation passes.

Checked in the real Windows desktop app (Python 3.12 virtual environment, Czech system locale): the validation message for an empty prompt, a Czech prompt with diacritics, a clear error and a clean return to the idle state when no model is downloaded, and the Stop button while the worker is starting.

## Real hardware: Windows 11 + NVIDIA RTX 4060 (8 GB VRAM) — 2026-10-18

Environment: Windows 11, Python 3.12, CUDA build of PyTorch, diffusers 0.36.0, transformers 4.57.6, Czech system locale. Every model was downloaded through the app into the standard data directory and generated through the GUI (offline worker).

| Model | Result on the RTX 4060 |
|---|---|
| Stable Diffusion 1.5 | Works on CUDA and on CPU (slow). |
| SDXL Turbo | Works. |
| SDXL Base | Works. 8 GB is close to the limit; keep **Save VRAM with CPU offload** enabled. |
| AudioLDM 2 | Works after the fix below; 5 s of audio in about 7 s. |
| LTX Video | **Not verified.** The 28 GB download was stopped before it finished. The T5-XXL text encoder alone needs about 9.5 GB in bf16, more than the 8 GB of VRAM, so `enable_model_cpu_offload()` is expected to run out of memory. A layer-wise offload or CPU text encoding would be needed and has not been implemented or tested. |

Found and fixed:

- **AudioLDM 2 failed** with `'GPT2Model' object has no attribute '_get_initial_cache_position'`. The repository declares its language model as `GPT2Model`, which transformers 4.50 and later no longer equips with the generation helpers the pipeline calls. The worker now loads the same weights as `GPT2LMHeadModel` and passes them to the pipeline. A unit test checks that only AudioLDM 2 receives this component.
- **Downloads fetched a second, unused UNet.** SD 1.5 ships `*.non_ema.safetensors` (3.4 GB). It is now ignored: the SD 1.5 download is about 5.5 GB instead of 8.9 GB. Folders downloaded before this change can keep the extra file; deleting `unet/diffusion_pytorch_model.non_ema.safetensors` is safe.

Also confirmed in the real app: validation message for an empty prompt, Czech prompt with diacritics, clean error when no model is downloaded, the Stop button during loading, and an output path containing `č` and `ř`.

Observed but not changed (candidates for the next version):

- `Setup-AI-GPU.bat` installs PyTorch from PyPI, which is a CPU-only build on Windows. On a fresh install generation runs on the CPU. NVIDIA users need a CUDA build (`--index-url https://download.pytorch.org/whl/cu128`).
- `enable_vae_slicing()` and the `torch_dtype` argument produce deprecation warnings in the current libraries.
- After a model download the numeric settings are reset to the model defaults.
- The model is reloaded for every generation; keeping it loaded would speed up repeated runs.
- CPU offload is on by default, which makes small models (SD 1.5, SDXL Turbo) slower than necessary on a GPU with enough VRAM.
- Downloads are fp32 and converted on load; fp16 variants would roughly halve disk use.

Not verified: LTX Video, GPU backends other than this NVIDIA card (AMD ROCm, Intel XPU, Apple MPS), macOS, import of a local model folder, and air-gapped installation on a separate machine.

## Follow-up fixes — 2026-10-18

Made after the hardware run, verified by unit tests and the CI workflow only (not on the RTX 4060 again):

- **`Setup-AI-GPU.bat` installed a CPU-only PyTorch on Windows.** `setup_ai.py` has a new `--backend cuda`. It reads `nvidia-smi`, picks the newest of CUDA 13.0 / 12.8 / 12.6 that the driver supports (or `--cuda-build`), removes a CPU-only PyTorch from the project environment, installs the CUDA wheel and warns if the GPU is still not usable. The launcher uses it. Unit tests cover the driver-to-build mapping, the pip arguments and the launcher. The actual wheel installation was not run here (the PyTorch download host is not reachable from the test environment).
- **Numeric settings were reset after a model download** (steps, guidance, resolution returned to the model defaults). Only the "Downloaded" note is refreshed now. The GUI smoke test checks this.
- **Deprecation warning for `enable_vae_slicing`** is gone: slicing is enabled on the VAE directly. A unit test checks that the deprecated call is not used.
- **CI** has a new `gui` job that runs the offscreen Qt smoke test with PySide6 on Ubuntu.

Still open: LTX Video on 8 GB VRAM, keeping a model loaded between generations, smarter offload defaults, fp16 downloads, the `torch_dtype` warning (raised inside diffusers/transformers, harmless).
