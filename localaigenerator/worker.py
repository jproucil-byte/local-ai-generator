"""Isolated subprocess: models are loaded locally, cancellation terminates this process."""
import argparse
import gc
import json
import os
from pathlib import Path
import sys
import traceback
from datetime import datetime, timezone
from uuid import uuid4
from .catalog import get_model
from .core import Request, model_root, select_device


def emit(event, **values):
    # ASCII-only JSON: the GUI decodes the pipe as UTF-8, but Windows pipes use the system
    # code page (e.g. cp1250), so non-ASCII text (diacritics in paths, "…") would be dropped.
    print(json.dumps({"event": event, **values}), flush=True)


def generate(request):
    request.validate()
    # Set before importing Hub/Transformers. No downloader exists in this code path.
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    import torch
    import diffusers
    model = get_model(request.model)
    source = Path(request.local_model).expanduser() if request.local_model else model_root() / model.key
    if not request.local_model and not any((source / name).is_file() for name in (".localaigenerator-complete", ".localaigenerator-complete")):
        raise ValueError("The model download is incomplete. Select Download model again to resume.")
    if not (source / "model_index.json").is_file():
        raise ValueError("The model is not ready. Download it in the app or select a complete Diffusers folder.")
    device = select_device(torch, request.device)
    dtype = torch.float32
    if device in ("cuda", "xpu"):
        dtype = torch.bfloat16 if model.kind == "video" and device == "cuda" and torch.cuda.is_bf16_supported() else torch.float16
    # float32 on MPS is conservative; unsupported operations fail with a CPU recommendation.
    emit("status", text=f"Loading {model.name} on {device.upper()}…")
    components = {}
    if model.pipeline == "AudioLDM2Pipeline":
        # The repository declares its language model as GPT2Model, which transformers >= 4.50 no longer
        # equips with the generation helpers the pipeline calls (_get_initial_cache_position). The same
        # weights load as GPT2LMHeadModel (tied head), which has them in every supported version.
        from transformers import GPT2LMHeadModel
        components["language_model"] = GPT2LMHeadModel.from_pretrained(str(source.resolve() / "language_model"), local_files_only=True, torch_dtype=dtype, use_safetensors=True)
    pipe = getattr(diffusers, model.pipeline).from_pretrained(str(source.resolve()), local_files_only=True, torch_dtype=dtype, use_safetensors=True, **components)
    pipe.set_progress_bar_config(disable=True)
    if device == "cuda" and request.offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(device)
    if hasattr(pipe, "enable_vae_slicing"):
        pipe.enable_vae_slicing()
    if hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_tiling"):
        pipe.vae.enable_tiling()
    seed = request.seed if request.seed >= 0 else int.from_bytes(os.urandom(4), "little")
    generator_device = device if device in ("cuda", "xpu") else "cpu"
    kwargs = dict(prompt=request.prompt, negative_prompt=request.negative or None, num_inference_steps=request.steps, guidance_scale=request.guidance, generator=torch.Generator(device=generator_device).manual_seed(seed))
    if model.kind in ("image", "video"):
        kwargs.update(width=request.width, height=request.height)
    if model.kind == "audio":
        kwargs["audio_length_in_s"] = request.seconds
    if model.kind == "video":
        kwargs.update(num_frames=request.frames, frame_rate=request.fps, decode_timestep=0.05, decode_noise_scale=0.025)

    def progress(pipeline, step, timestep, callback_kwargs):
        emit("progress", value=int(100 * (step + 1) / request.steps))
        return callback_kwargs

    # AudioLDM2 0.36 uses the legacy callback, image/LTX use the step-end callback.
    if model.kind == "audio":
        kwargs.update(callback=lambda step, timestep, latents: emit("progress", value=min(99, int(100 * (step + 1) / request.steps))), callback_steps=1)
    else:
        kwargs["callback_on_step_end"] = progress
    emit("status", text="Generating locally. The first load may take a while.")
    output_dir = Path(request.output).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    # Unique directory reserves the output even with concurrent instances.
    job_dir = output_dir / (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:12])
    job_dir.mkdir(exist_ok=False)
    temporary = job_dir / "pending"
    extension = {"image": ".png", "video": ".mp4", "audio": ".wav"}[model.kind]
    target = job_dir / ("creation" + extension)
    try:
        with torch.inference_mode():
            result = pipe(**kwargs)
        if model.kind == "image":
            if getattr(result, "nsfw_content_detected", None) and any(result.nsfw_content_detected):
                raise ValueError("The model safety filter blocked this output. Revise your prompt.")
            result.images[0].save(temporary, format="PNG")
        elif model.kind == "audio":
            import soundfile
            soundfile.write(str(temporary), result.audios[0], 16000, format="WAV", subtype="PCM_16")
        else:
            from diffusers.utils import export_to_video
            temporary = job_dir / "pending.mp4"
            export_to_video(result.frames[0], str(temporary), fps=request.fps)
        temporary.replace(target)
        metadata = {**request.to_dict(), "seed": seed, "resolved_device": device, "model_repo": model.repo, "created_utc": datetime.now(timezone.utc).isoformat()}
        (job_dir / "creation.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        del pipe
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
    emit("done", path=str(target.resolve()), seed=seed)


def download(key):
    from huggingface_hub import snapshot_download
    model = get_model(key)
    emit("status", text=f"Downloading {model.name}. Models may require several to tens of GB.")
    target = model_root() / key
    (target / ".localaigenerator-complete").unlink(missing_ok=True)
    # Only Diffusers component weights, not every single-file checkpoint in the repo.
    snapshot_download(repo_id=model.repo, local_dir=str(target), allow_patterns=["*.json", "*/*.safetensors", "*.txt", "*.model", "*.tiktoken", "README*", "LICENSE*", "NOTICE*"], ignore_patterns=["*.fp16.*", "*.non_ema.*", "*.onnx", "*.msgpack"])
    if not (target / "model_index.json").is_file():
        raise ValueError("The repository does not contain a complete Diffusers configuration.")
    (target / ".localaigenerator-complete").write_text(model.repo, encoding="utf-8")
    emit("done", path=str(model_root() / key), download=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["generate", "download", "hardware"])
    parser.add_argument("--model")
    args = parser.parse_args()
    try:
        if args.action == "generate":
            generate(Request(**json.loads(sys.stdin.read())))
        elif args.action == "download":
            download(args.model)
        else:
            import torch
            device = select_device(torch)
            name = torch.cuda.get_device_name(0) if device == "cuda" else device.upper()
            emit("done", device=device, name=name, torch_version=torch.__version__)
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        emit("error", text=str(exc) + "\nIf memory is insufficient or a GPU operation fails, reduce the resolution, select a smaller model, or use CPU.")
        sys.exit(1)


if __name__ == "__main__":
    main()
