"""Placeholder image generation helpers for Ken Burns renders."""
from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

from .models import AssetPlan


@dataclass(slots=True)
class PlaceholderStyle:
    """Defines the base palette and typography for generated frames."""

    background: Tuple[int, int, int]
    accent: Tuple[int, int, int]
    text: Tuple[int, int, int]
    font_size: int = 72


_STYLE_PRESETS: Dict[str, PlaceholderStyle] = {
    "cinematic realism": PlaceholderStyle(
        background=(15, 23, 42), accent=(99, 102, 241), text=(248, 250, 252)
    ),
    "futuristic neon": PlaceholderStyle(
        background=(8, 11, 24), accent=(6, 182, 212), text=(236, 72, 153)
    ),
    "warm and nostalgic": PlaceholderStyle(
        background=(45, 34, 24), accent=(217, 119, 6), text=(254, 243, 199)
    ),
    "dramatic and intense": PlaceholderStyle(
        background=(20, 20, 20), accent=(239, 68, 68), text=(252, 211, 77)
    ),
}


class PlaceholderImageFactory:
    """Creates stylised frames when bespoke artwork is unavailable."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create(self, asset: AssetPlan, *, style_hint: str | None = None) -> Path:
        """Generate a placeholder image for the provided asset plan."""
        style = _STYLE_PRESETS.get(style_hint or asset.metadata.get("style", ""))
        if style is None:
            style = _STYLE_PRESETS["cinematic realism"]

        file_name = f"{asset.identifier.replace(' ', '_')}.png"
        path = self.output_dir / file_name
        prompt = asset.metadata.get("prompt") or asset.description
        keywords = asset.metadata.get("keywords", "")
        mood = asset.metadata.get("mood", "Cinematic")

        image = Image.new("RGB", (1920, 1080), color=style.background)
        draw = ImageDraw.Draw(image)

        self._draw_gradient(draw, image.size, style)

        title_font = self._load_font(style.font_size)
        subtitle_font = self._load_font(int(style.font_size * 0.5))

        wrapped_prompt = textwrap.fill(prompt, width=32)
        draw.text((120, 200), wrapped_prompt, font=title_font, fill=style.text)

        keyword_text = f"Mood: {mood}\nKeywords: {keywords}" if keywords else f"Mood: {mood}"
        draw.text((120, 720), textwrap.fill(keyword_text, width=40), font=subtitle_font, fill=style.text)

        image.save(path)
        asset.source_uri = str(path)
        return path

    def _draw_gradient(
        self, draw: ImageDraw.ImageDraw, size: Tuple[int, int], style: PlaceholderStyle
    ) -> None:
        width, height = size
        for y in range(height):
            blend = y / height
            color = tuple(
                int(style.background[i] * (1 - blend) + style.accent[i] * blend)
                for i in range(3)
            )
            draw.line([(0, y), (width, y)], fill=color)

        circle_radius = int(math.hypot(width, height) * 0.1)
        center = (int(width * 0.85), int(height * 0.2))
        draw.ellipse(
            [
                (center[0] - circle_radius, center[1] - circle_radius),
                (center[0] + circle_radius, center[1] + circle_radius),
            ],
            outline=style.text,
            width=6,
        )

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:  # pragma: no cover - environment dependent fallback
            return ImageFont.load_default()


__all__ = ["PlaceholderImageFactory"]
