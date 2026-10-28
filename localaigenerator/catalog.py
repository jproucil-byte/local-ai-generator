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
    Model("sd15", "Stable Diffusion 1.5", "image", "stable-diffusion-v1-5/stable-diffusion-v1-5", "StableDiffusionPipeline", 512, 512, 25, 7.5, "A smaller image model. CPU generation is supported but slow. License: see the model card."),
    Model("sdxl", "SDXL Base", "image", "stabilityai/stable-diffusion-xl-base-1.0", "StableDiffusionXLPipeline", 1024, 1024, 30, 5.0, "More detailed images with higher memory requirements. License: see the model card."),
    Model("turbo", "SDXL Turbo", "image", "stabilityai/sdxl-turbo", "StableDiffusionXLPipeline", 512, 512, 4, 0.0, "Fast previews. Use 1–4 steps and guidance 0. License: see the model card."),
    Model("ltx", "LTX Video", "video", "Lightricks/LTX-Video", "LTXPipeline", 512, 320, 30, 5.0, "Experimental short videos. A powerful GPU is recommended; CPU may be impractical. License: see the model card."),
    Model("audioldm2", "AudioLDM 2", "audio", "cvssp/audioldm2", "AudioLDM2Pipeline", 512, 512, 50, 3.5, "Sounds and short musical textures, 16 kHz. CC-BY-NC-SA-4.0: non-commercial use only."),
)


def get_model(key):
    for model in MODELS:
        if model.key == key:
            return model
    raise ValueError("Unknown model: " + key)
