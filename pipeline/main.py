"""Controller for transforming narrative text into structured scene plans."""
from __future__ import annotations

import itertools
import logging
import re
from typing import Callable, Iterable, List, Mapping, Sequence

from .models import (
    AssetPlan,
    KenBurnsSegment,
    ScenePlan,
    ShotPlan,
    TTSChunk,
    VideoClipReference,
)
from .scheduler import PipelineScheduler, PipelineStage, StageTask

_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


class StoryPipelineController:
    """High-level orchestrator for generating and scheduling scene plans."""

    def __init__(
        self,
        scheduler: PipelineScheduler | None = None,
        logger: logging.Logger | None = None,
        default_voice: str = "default",
        narration_words_per_second: float = 2.5,
        minimum_segment_duration: float = 6.0,
    ) -> None:
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.scheduler = scheduler or PipelineScheduler(self.logger)
        self.default_voice = default_voice
        self.words_per_second = narration_words_per_second
        self.minimum_segment_duration = minimum_segment_duration

    def ingest_story(
        self,
        story_text: str,
        inserted_clips: Mapping[str, Sequence[VideoClipReference]] | None = None,
    ) -> List[ScenePlan]:
        """Convert free-form story text into structured scene plans."""
        paragraphs = [paragraph.strip() for paragraph in story_text.split("\n\n") if paragraph.strip()]
        scenes: List[ScenePlan] = []
        inserted_clips = inserted_clips or {}

        for index, paragraph in enumerate(paragraphs, start=1):
            summary = paragraph.splitlines()[0]
            scene = ScenePlan(name=f"Scene {index}", summary=summary)

            for shot_number, sentence in enumerate(self._split_sentences(paragraph), start=1):
                shot_name = f"Shot {index}.{shot_number}"
                shot = self._build_shot_plan(
                    scene_index=index,
                    shot_index=shot_number,
                    sentence=sentence,
                    shot_name=shot_name,
                    supplemental_clips=inserted_clips.get(shot_name, ()),
                )

                scene.add_shot(shot)

            if not scene.shots:
                self.logger.warning("Scene '%s' generated without shots", scene.name)
                scene.total_duration = 0.0
            else:
                scene.total_duration = sum(shot.clip_duration for shot in scene.shots)
            scenes.append(scene)

        return scenes

    def build_schedule(self, scenes: Sequence[ScenePlan]) -> None:
        """Populate the scheduler with tasks derived from the given scenes."""
        for scene in scenes:
            self.scheduler.schedule_scene(scene)

    def plan_and_schedule(
        self,
        story_text: str,
        inserted_clips: Mapping[str, Sequence[VideoClipReference]] | None = None,
    ) -> Sequence[ScenePlan]:
        """Produce scene plans from text and enqueue all downstream tasks."""
        scenes = self.ingest_story(story_text, inserted_clips=inserted_clips)
        self.build_schedule(scenes)
        return scenes

    def run(self, handler: Callable[[StageTask], None]) -> None:
        """Execute the scheduled tasks with the provided handler."""
        self.scheduler.run(handler)

    @staticmethod
    def _split_sentences(paragraph: str) -> List[str]:
        sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT_PATTERN.split(paragraph.strip()) if sentence.strip()]
        return sentences

    def _estimate_duration(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        return max(self.minimum_segment_duration, len(words) / self.words_per_second)

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

    def _build_shot_plan(
        self,
        scene_index: int,
        shot_index: int,
        sentence: str,
        shot_name: str,
        supplemental_clips: Sequence[VideoClipReference],
    ) -> ShotPlan:
        narration_chunks = self._chunk_narration(sentence, shot_name)
        ken_burns_segments = self._plan_ken_burns_segments(shot_name, narration_chunks)
        inferred_assets = list(self._infer_assets_from_sentence(sentence, shot_name))

        clip_duration = sum(segment.duration for segment in ken_burns_segments)
        if supplemental_clips:
            clip_duration += sum(clip.duration for clip in supplemental_clips)

        clip_duration = max(clip_duration, self._estimate_duration(sentence))

        shot = ShotPlan(
            name=shot_name,
            clip_duration=clip_duration,
            visual_prompt=sentence,
            narration_text=sentence,
        )

        for asset in inferred_assets:
            shot.add_asset(asset)

        for chunk in narration_chunks:
            shot.add_tts_chunk(chunk)
            shot.add_asset(
                AssetPlan(
                    identifier=f"{chunk.identifier}-audio",
                    asset_type="tts_chunk",
                    description=f"Synthesised narration chunk {chunk.chunk_index} for {shot_name}",
                    duration=chunk.duration,
                    start_time=chunk.start_offset,
                    end_time=chunk.end_offset,
                    metadata={"voice": chunk.voice, "text": chunk.text},
                )
            )

        shot_audio_duration = narration_chunks[-1].end_offset if narration_chunks else 0.0
        effective_audio_duration = max(shot_audio_duration, clip_duration)
        shot.audio_track = AssetPlan(
            identifier=f"{shot_name}-narration",
            asset_type="audio_track",
            description=f"Compiled narration for {shot_name}",
            duration=effective_audio_duration,
            metadata={
                "voice": self.default_voice,
                "narration_duration": f"{shot_audio_duration:.2f}",
            },
        )

        for segment in ken_burns_segments:
            shot.add_ken_burns_segment(segment)

        for idx, clip in enumerate(supplemental_clips, start=1):
            clip_identifier = f"{shot_name}-clip-{idx}"
            reference = VideoClipReference(
                identifier=clip_identifier,
                source_uri=clip.source_uri,
                duration=clip.duration,
                insertion_offset=clip.insertion_offset,
                description=clip.description,
            )
            shot.add_inserted_clip(reference)
            shot.add_asset(
                AssetPlan(
                    identifier=f"{clip_identifier}-asset",
                    asset_type="external_clip",
                    description=f"External clip for {shot_name}",
                    source_uri=clip.source_uri,
                    duration=clip.duration,
                    start_time=clip.insertion_offset,
                    end_time=clip.insertion_offset + clip.duration,
                )
            )

        shot.assembled_video = AssetPlan(
            identifier=f"{shot_name}-kenburns",
            asset_type="ken_burns_video",
            description=f"Ken Burns render for {shot_name}",
            duration=clip_duration,
        )

        return shot

    def _chunk_narration(self, text: str, shot_name: str) -> List[TTSChunk]:
        if not text:
            return []

        words = text.split()
        chunk_words: List[str] = []
        chunk_index = 0
        chunks: List[TTSChunk] = []
        start_offset = 0.0

        for word in words:
            chunk_words.append(word)
            if len(chunk_words) >= 40:
                chunk_index += 1
                chunk_text = " ".join(chunk_words)
                duration = max(self.minimum_segment_duration, len(chunk_words) / self.words_per_second)
                chunks.append(
                    TTSChunk(
                        identifier=f"{shot_name}-tts-{chunk_index}",
                        text=chunk_text,
                        chunk_index=chunk_index,
                        start_offset=start_offset,
                        duration=duration,
                        voice=self.default_voice,
                    )
                )
                start_offset += duration
                chunk_words = []

        if chunk_words:
            chunk_index += 1
            chunk_text = " ".join(chunk_words)
            duration = max(self.minimum_segment_duration, len(chunk_words) / self.words_per_second)
            chunks.append(
                TTSChunk(
                    identifier=f"{shot_name}-tts-{chunk_index}",
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_offset=start_offset,
                    duration=duration,
                    voice=self.default_voice,
                )
            )

        return chunks

    def _plan_ken_burns_segments(
        self, shot_name: str, chunks: Sequence[TTSChunk]
    ) -> List[KenBurnsSegment]:
        if not chunks:
            return []

        directions = itertools.cycle(["left_to_right", "right_to_left", "center_pull"])
        segments: List[KenBurnsSegment] = []
        current_offset = 0.0

        for chunk in chunks:
            duration = max(self.minimum_segment_duration, chunk.duration)
            direction = next(directions)
            segment = KenBurnsSegment(
                identifier=f"{shot_name}-kb-{chunk.chunk_index}",
                asset_identifier=f"{shot_name}-visual",
                duration=duration,
                zoom_start=1.0,
                zoom_end=1.1 if direction != "center_pull" else 1.2,
                pan_direction=direction,
                start_offset=current_offset,
            )
            segments.append(segment)
            current_offset += duration

        return segments


__all__ = ["StoryPipelineController", "PipelineStage", "StageTask"]
