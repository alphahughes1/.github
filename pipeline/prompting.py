"""Utilities for turning narration sentences into rich image prompts."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List


_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "so",
    "because",
    "of",
    "for",
    "in",
    "on",
    "with",
    "to",
    "their",
    "his",
    "her",
    "its",
    "is",
    "are",
    "was",
    "were",
    "be",
    "as",
    "at",
    "by",
    "they",
    "them",
    "he",
    "she",
    "it",
    "we",
    "you",
    "i",
    "from",
    "into",
    "over",
    "under",
    "that",
    "this",
    "these",
    "those",
}

_WORD_PATTERN = re.compile(r"[A-Za-z']+")


@dataclass(slots=True)
class PromptDetails:
    """Structured description of an image generation prompt."""

    prompt: str
    negative_prompt: str
    keywords: List[str]
    style: str
    mood: str
    aspect_ratio: str = "16:9"

    def to_metadata(self) -> Dict[str, str]:
        """Convert the prompt into serialisable metadata for an asset plan."""
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "keywords": ", ".join(self.keywords),
            "style": self.style,
            "mood": self.mood,
            "aspect_ratio": self.aspect_ratio,
        }


class PromptGenerator:
    """Derive cinematic prompts and keywords from narration sentences."""

    def __init__(self, default_style: str = "cinematic realism") -> None:
        self.default_style = default_style

    def build_prompt(self, sentence: str) -> PromptDetails:
        """Create a prompt tuned for diffusion/vision models."""
        cleaned_sentence = " ".join(sentence.strip().split())
        keywords = self._extract_keywords(cleaned_sentence)
        mood = self._infer_mood(keywords)

        prompt = (
            f"{cleaned_sentence}. {self.default_style.title()} lighting, {mood} mood,"
            " ultra high definition, detailed textures, DSLR depth of field"
        )
        negative_prompt = (
            "low quality, blurry, pixelated, distorted faces, extra limbs, text artifacts"
        )

        return PromptDetails(
            prompt=prompt,
            negative_prompt=negative_prompt,
            keywords=keywords,
            style=self.default_style,
            mood=mood,
        )

    def _extract_keywords(self, sentence: str) -> List[str]:
        tokens = [word.lower() for word in _WORD_PATTERN.findall(sentence)]
        keywords = [token for token in tokens if token not in _STOPWORDS]
        unique: List[str] = []
        for token in keywords:
            if token not in unique:
                unique.append(token)
        return unique[:8]

    def _infer_mood(self, keywords: Iterable[str]) -> str:
        keyword_set = {word.lower() for word in keywords}
        if keyword_set & {"dark", "mysterious", "shadow", "midnight"}:
            return "moody cinematic"
        if keyword_set & {"love", "warm", "sunset", "family"}:
            return "warm and nostalgic"
        if keyword_set & {"battle", "storm", "tension", "urgent"}:
            return "dramatic and intense"
        if keyword_set & {"future", "neon", "cyber", "tech"}:
            return "futuristic neon"
        return "uplifting and hopeful"


__all__ = ["PromptGenerator", "PromptDetails"]
