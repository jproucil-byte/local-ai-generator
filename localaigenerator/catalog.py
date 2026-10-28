from dataclasses import dataclass


@dataclass(frozen=True)
class Model:
    key: str
    name: str
    kind: str
    repo: str
    pipeline: str
    width: int
    height: int
    steps: int
    guidance: float
    note: str

    @property
    def url(self):
        return "https://huggingface.co/" + self.repo


MODELS = (
    Model("sd15", "Stable Diffusion 1.5", "image", "stable-diffusion-v1-5/stable-diffusion-v1-5", "StableDiffusionPipeline", 512, 512, 25, 7.5, "Menší obrazový model. CPU je možné, ale pomalé. Licence: viz karta modelu."),
    Model("sdxl", "SDXL Base", "image", "stabilityai/stable-diffusion-xl-base-1.0", "StableDiffusionXLPipeline", 1024, 1024, 30, 5.0, "Detailnější obrázky; výrazně vyšší nároky na paměť. Licence: viz karta modelu."),
    Model("turbo", "SDXL Turbo", "image", "stabilityai/sdxl-turbo", "StableDiffusionXLPipeline", 512, 512, 4, 0.0, "Rychlé náhledy. 1–4 kroky, guidance 0. Licence: viz karta modelu."),
    Model("ltx", "LTX Video", "video", "Lightricks/LTX-Video", "LTXPipeline", 512, 320, 30, 5.0, "Experimentální krátká videa; výkonné GPU doporučeno. CPU může být nepraktické. Licence: viz karta modelu."),
    Model("audioldm2", "AudioLDM 2", "audio", "cvssp/audioldm2", "AudioLDM2Pipeline", 512, 512, 50, 3.5, "Zvuky a krátké hudební textury, 16 kHz. CC-BY-NC-SA-4.0: pouze nekomerční použití."),
)


def get_model(key):
    for model in MODELS:
        if model.key == key:
            return model
    raise ValueError("Neznámý model: " + key)
