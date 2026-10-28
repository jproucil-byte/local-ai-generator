import json
import os
import platform
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from .catalog import get_model


def data_root():
    override = os.environ.get("LOCALAIGENERATOR_HOME") or os.environ.get("LOCALAIGENERATOR_HOME")
    if override:
        return Path(override).expanduser()
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        target, legacy = base / "LocalAiGenerator", base / "LocalAiGenerator"
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
        target, legacy = base / "LocalAiGenerator", base / "LocalAiGenerator"
    else:
        base = Path(os.environ["XDG_DATA_HOME"]) if os.environ.get("XDG_DATA_HOME") else Path.home() / ".local/share"
        target, legacy = base / "local-ai-generator", base / "local-ai-generator"
    # Reuse existing weights and settings after the branding change.
    return legacy if legacy.exists() and not target.exists() else target


def model_root():
    return data_root() / "models"


def select_device(torch, requested="auto"):
    cuda = torch.cuda.is_available()
    mps = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    xpu = hasattr(torch, "xpu") and torch.xpu.is_available()
    available = {"cpu": True, "cuda": cuda, "mps": mps, "xpu": xpu}
    if requested == "auto":
        return next(d for d in ("cuda", "mps", "xpu", "cpu") if available[d])
    if requested not in available or not available[requested]:
        raise ValueError(f"Device {requested} is unavailable. Select Auto or CPU.")
    return requested


@dataclass
class Request:
    model: str
    prompt: str
    output: str
    negative: str = ""
    device: str = "auto"
    width: int = 512
    height: int = 512
    steps: int = 25
    guidance: float = 7.5
    seed: int = -1
    seconds: float = 5.0
    frames: int = 25
    fps: int = 24
    offload: bool = True
    local_model: str = ""

    def validate(self):
        model = get_model(self.model)
        if not self.prompt.strip():
            raise ValueError("Enter a description of what you want to create.")
        if not self.output.strip():
            raise ValueError("Choose an output folder.")
        if not 1 <= self.steps <= 150 or not 0 <= self.guidance <= 30:
            raise ValueError("Steps must be 1–150 and guidance must be 0–30.")
        if not -1 <= self.seed <= 2**32 - 1:
            raise ValueError("Seed must be -1 or an integer from 0 to 4294967295.")
        if self.device not in ("auto", "cuda", "mps", "xpu", "cpu"):
            raise ValueError("Unknown device.")
        if model.kind != "audio":
            divisor = 32 if model.kind == "video" else 8
            if any(n < 256 or n > 2048 or n % divisor for n in (self.width, self.height)):
                raise ValueError(f"Dimensions must be 256–2048 and multiples of {divisor}.")
        if model.kind == "video" and (not 9 <= self.frames <= 161 or (self.frames - 1) % 8 or not 1 <= self.fps <= 60):
            raise ValueError("LTX requires 8n+1 frames (9–161) and 1–60 FPS.")
        if model.kind == "audio" and not 1 <= self.seconds <= 10:
            raise ValueError("Audio duration must be 1–10 seconds.")
        if model.key == "turbo" and (self.steps > 4 or self.guidance != 0):
            raise ValueError("SDXL Turbo requires 1–4 steps and guidance 0.")
        return self

    def to_dict(self):
        return asdict(self)


def save_settings(values):
    root = data_root()
    root.mkdir(parents=True, exist_ok=True)
    target = root / "settings.json"
    temporary = root / ("settings-" + secrets.token_hex(6) + ".tmp")
    temporary.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)


def load_settings():
    try:
        result = json.loads((data_root() / "settings.json").read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}
