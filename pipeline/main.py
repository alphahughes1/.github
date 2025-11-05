"""Controller for transforming narrative text into structured scene plans."""
from __future__ import annotations

import logging
import re
from typing import Callable, Iterable, List, Sequence

from .models import AssetPlan, ScenePlan, ShotPlan
from .scheduler import PipelineScheduler, PipelineStage, StageTask

_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


class StoryPipelineController:
    """High-level orchestrator for generating and scheduling scene plans."""

    def __init__(
        self,
        scheduler: PipelineScheduler | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.scheduler = scheduler or PipelineScheduler(self.logger)

    def ingest_story(self, story_text: str) -> List[ScenePlan]:
        """Convert free-form story text into structured scene plans."""
        paragraphs = [paragraph.strip() for paragraph in story_text.split("\n\n") if paragraph.strip()]
        scenes: List[ScenePlan] = []

        for index, paragraph in enumerate(paragraphs, start=1):
            summary = paragraph.splitlines()[0]
            scene = ScenePlan(name=f"Scene {index}", summary=summary)

            for shot_number, sentence in enumerate(self._split_sentences(paragraph), start=1):
                shot_name = f"Shot {index}.{shot_number}"
                shot = ShotPlan(
                    name=shot_name,
                    clip_duration=self._estimate_duration(sentence),
                    visual_prompt=sentence,
                    narration_text=sentence,
                )
                for asset in self._infer_assets_from_sentence(sentence, shot_name):
                    shot.add_asset(asset)

                scene.add_shot(shot)

            if not scene.shots:
                self.logger.warning("Scene '%s' generated without shots", scene.name)
            scenes.append(scene)

        return scenes

    def build_schedule(self, scenes: Sequence[ScenePlan]) -> None:
        """Populate the scheduler with tasks derived from the given scenes."""
        for scene in scenes:
            self.scheduler.schedule_scene(scene)

    def plan_and_schedule(self, story_text: str) -> Sequence[ScenePlan]:
        """Produce scene plans from text and enqueue all downstream tasks."""
        scenes = self.ingest_story(story_text)
        self.build_schedule(scenes)
        return scenes

    def run(self, handler: Callable[[StageTask], None]) -> None:
        """Execute the scheduled tasks with the provided handler."""
        self.scheduler.run(handler)

    @staticmethod
    def _split_sentences(paragraph: str) -> List[str]:
        sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT_PATTERN.split(paragraph.strip()) if sentence.strip()]
        return sentences

    @staticmethod
    def _estimate_duration(sentence: str, words_per_second: float = 2.5) -> float:
        words = sentence.split()
        if not words:
            return 0.0
        return max(2.0, len(words) / words_per_second)

    def _infer_assets_from_sentence(self, sentence: str, shot_name: str) -> Iterable[AssetPlan]:
        assets: List[AssetPlan] = []
        lower_sentence = sentence.lower()

        assets.append(
            AssetPlan(
                identifier=f"{shot_name}-visual",
                asset_type="image_prompt",
                description=f"Illustrate: {sentence}",
            )
        )
        assets.append(
            AssetPlan(
                identifier=f"{shot_name}-voice",
                asset_type="voiceover",
                description="Narration track for the associated sentence.",
                metadata={"script": sentence},
            )
        )

        if any(keyword in lower_sentence for keyword in ("music", "song", "melody")):
            assets.append(
                AssetPlan(
                    identifier=f"{shot_name}-music",
                    asset_type="audio",
                    description="Background music inspired by the sentence mood.",
                )
            )

        if any(keyword in lower_sentence for keyword in ("character", "hero", "villain")):
            assets.append(
                AssetPlan(
                    identifier=f"{shot_name}-character-design",
                    asset_type="concept_art",
                    description="Character concept reference derived from the sentence.",
                )
            )

        return assets


__all__ = ["StoryPipelineController", "PipelineStage", "StageTask"]
