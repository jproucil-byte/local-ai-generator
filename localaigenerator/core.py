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
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        target, legacy = base / "LocalAiGenerator", base / "LocalAiGenerator"
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
        target, legacy = base / "LocalAiGenerator", base / "LocalAiGenerator"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
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
        raise ValueError(f"Zařízení {requested} není dostupné. Zvolte Auto nebo CPU.")
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
            raise ValueError("Zadejte popis toho, co chcete vytvořit.")
        if not self.output.strip():
            raise ValueError("Vyberte výstupní složku.")
        if not 1 <= self.steps <= 150 or not 0 <= self.guidance <= 30:
            raise ValueError("Kroky musí být 1–150, guidance 0–30.")
        if not -1 <= self.seed <= 2**32 - 1:
            raise ValueError("Seed musí být -1 nebo celé číslo 0–4294967295.")
        if self.device not in ("auto", "cuda", "mps", "xpu", "cpu"):
            raise ValueError("Neznámé zařízení.")
        if model.kind != "audio":
            divisor = 32 if model.kind == "video" else 8
            if any(n < 256 or n > 2048 or n % divisor for n in (self.width, self.height)):
                raise ValueError(f"Rozměry musí být 256–2048 a násobky {divisor}.")
        if model.kind == "video" and (not 9 <= self.frames <= 161 or (self.frames - 1) % 8 or not 1 <= self.fps <= 60):
            raise ValueError("LTX: počet snímků musí být 8n+1 (9–161), FPS 1–60.")
        if model.kind == "audio" and not 1 <= self.seconds <= 10:
            raise ValueError("Zvuk: délka musí být 1–10 sekund.")
        if model.key == "turbo" and (self.steps > 4 or self.guidance != 0):
            raise ValueError("SDXL Turbo vyžaduje 1–4 kroky a guidance 0.")
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
