from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.config import Settings, get_settings, new_trace_id
from app.core.logging import get_logger
from app.services.openai_client import OpenAIClient


@dataclass(frozen=True)
class ImageGenerateResult:
    trace_id: str
    artifact_id: str
    image_path: str


class ImageService:
    def __init__(self, *, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.log = get_logger(__name__)
        self.client = OpenAIClient(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None

    async def generate(self, *, prompt: str, size: str = "1024x1024", transparent: bool = False) -> ImageGenerateResult:
        trace_id = new_trace_id()
        out_dir = self.settings.artifact_dir / "images" / trace_id
        out_dir.mkdir(parents=True, exist_ok=True)

        artifact_id = f"image-{trace_id}"
        out_path = out_dir / "image.png"

        if self.client is None:
            self._generate_dummy_image(out_path=out_path, prompt=prompt, size=size, transparent=transparent)
            self.log.info("Generated dummy image", extra={"trace_id": trace_id, "path": str(out_path)})
        else:
            res = await self.client.generate_image(prompt=prompt, size=size, transparent=transparent)
            out_path.write_bytes(res.png_bytes)
            self.log.info(
                "Generated image via OpenAI",
                extra={"trace_id": trace_id, "path": str(out_path), "model": res.model},
            )

        return ImageGenerateResult(trace_id=trace_id, artifact_id=artifact_id, image_path=str(out_path))

    def _generate_dummy_image(self, *, out_path: Path, prompt: str, size: str, transparent: bool) -> None:
        try:
            w_s, h_s = size.lower().split("x", 1)
            w, h = int(w_s), int(h_s)
        except Exception:
            w, h = 1024, 1024

        mode = "RGBA" if transparent else "RGB"
        bg = (0, 0, 0, 0) if transparent else (245, 245, 245)
        img = Image.new(mode, (w, h), bg)

        draw = ImageDraw.Draw(img)
        # Use default font; fonts-noto-cjk is installed in container, but PIL font discovery varies.
        try:
            font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 36)
        except Exception:
            font = ImageFont.load_default()

        text = f"Dummy Image\\n{size}\\n{prompt[:200]}"
        margin = 40
        draw.multiline_text((margin, margin), text, fill=(20, 20, 20), font=font, spacing=10)
        draw.rectangle([(10, 10), (w - 10, h - 10)], outline=(120, 120, 120), width=6)
        img.save(out_path, format="PNG")


