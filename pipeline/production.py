"""Media production utilities for assembling Ken Burns style films."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx import all as vfx
from pydub import AudioSegment
import pyttsx3

from .models import KenBurnsSegment, ScenePlan, ShotPlan, TTSChunk, VideoClipReference


class TTSAudioAssembler:
    """Synthesise narration audio chunks and stitch them into a master track."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def synthesise_shot(self, shot: ShotPlan, output_dir: Path) -> Path:
        """Generate a compiled narration WAV file for the provided shot."""
        if not shot.tts_chunks:
            raise ValueError(f"Shot '{shot.name}' does not define TTS chunks")

        output_dir.mkdir(parents=True, exist_ok=True)
        chunk_paths = []

        engine = pyttsx3.init()
        if shot.tts_chunks and shot.tts_chunks[0].voice:
            try:
                engine.setProperty("voice", shot.tts_chunks[0].voice)
            except Exception as exc:  # pragma: no cover - defensive configuration guard
                self._logger.warning("Unable to set voice '%s': %s", shot.tts_chunks[0].voice, exc)

        for chunk in shot.tts_chunks:
            chunk_path = output_dir / f"{chunk.identifier}.wav"
            self._logger.debug("Queueing TTS chunk '%s' -> %s", chunk.identifier, chunk_path)
            engine.save_to_file(chunk.text, str(chunk_path))
            chunk_paths.append(chunk_path)

        engine.runAndWait()

        combined = AudioSegment.silent(duration=0)
        for path in chunk_paths:
            self._logger.debug("Appending audio chunk %s", path)
            chunk_audio = AudioSegment.from_file(path)
            combined += chunk_audio

        target_duration_ms = int(round(shot.clip_duration * 1000))
        if target_duration_ms > len(combined):
            padding = target_duration_ms - len(combined)
            self._logger.debug("Padding narration with %sms of silence", padding)
            combined += AudioSegment.silent(duration=padding)

        master_path = output_dir / f"{shot.audio_track.identifier}.wav"
        combined.export(master_path, format="wav")

        shot.audio_track.source_uri = str(master_path)
        shot.audio_track.duration = shot.clip_duration
        return master_path


class KenBurnsRenderer:
    """Render Ken Burns movement clips and merge with inserted footage."""

    def __init__(
        self,
        resolution: tuple[int, int] = (1920, 1080),
        frame_rate: int = 30,
        logger: logging.Logger | None = None,
    ) -> None:
        self.resolution = resolution
        self.frame_rate = frame_rate
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def render_shot(
        self,
        shot: ShotPlan,
        image_assets: Mapping[str, str],
        output_dir: Path,
        supplemental_clips: Sequence[VideoClipReference] | None = None,
    ) -> Path:
        """Generate a Ken Burns style clip for a shot."""
        if not shot.ken_burns_segments:
            raise ValueError(f"Shot '{shot.name}' does not include Ken Burns segments")

        supplemental_clips = supplemental_clips or []
        output_dir.mkdir(parents=True, exist_ok=True)

        clips = []
        for segment in shot.ken_burns_segments:
            image_path = image_assets.get(segment.asset_identifier)
            if not image_path:
                raise FileNotFoundError(
                    f"Missing generated image for asset '{segment.asset_identifier}'"
                )
            self._logger.debug(
                "Rendering Ken Burns segment '%s' using %s", segment.identifier, image_path
            )
            clip = self._create_ken_burns_clip(Path(image_path), segment)
            clips.append(clip)

        for reference in supplemental_clips:
            clip_path = Path(reference.source_uri)
            if not clip_path.exists():
                raise FileNotFoundError(f"Supplemental clip '{clip_path}' not found")
            self._logger.debug("Adding supplemental clip %s", clip_path)
            clip = VideoFileClip(str(clip_path)).subclip(0, reference.duration)
            clips.insert(self._insertion_index_for(reference, clips), clip)

        final_clip = concatenate_videoclips(clips, method="compose")

        if shot.audio_track and shot.audio_track.source_uri:
            narration_audio = AudioFileClip(shot.audio_track.source_uri)
            final_clip = final_clip.set_audio(
                CompositeAudioClip([narration_audio.set_duration(final_clip.duration)])
            )

        output_path = output_dir / f"{shot.assembled_video.identifier}.mp4"
        try:
            final_clip.write_videofile(
                str(output_path),
                fps=self.frame_rate,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=str(output_dir / f"{shot.name}-temp-audio.m4a"),
                remove_temp=True,
                verbose=False,
                logger=None,
            )
        finally:
            final_clip.close()
            for clip in clips:
                if hasattr(clip, "close"):
                    clip.close()

        shot.assembled_video.source_uri = str(output_path)
        return output_path

    def _create_ken_burns_clip(self, image_path: Path, segment: KenBurnsSegment) -> ImageClip:
        clip = ImageClip(str(image_path)).set_duration(segment.duration)
        clip = clip.resize(newsize=self.resolution)
        center = {
            "left_to_right": (0.3, 0.5),
            "right_to_left": (0.7, 0.5),
            "center_pull": (0.5, 0.5),
        }.get(segment.pan_direction, (0.5, 0.5))
        clip = clip.fx(
            vfx.zoom_in,
            zoom=segment.zoom_end,
            duration=segment.duration,
            center=center,
        )
        return clip

    @staticmethod
    def _insertion_index_for(reference: VideoClipReference, clips: Sequence) -> int:
        elapsed = 0.0
        for index, clip in enumerate(clips):
            clip_duration = getattr(clip, "duration", 0.0)
            if reference.insertion_offset <= elapsed:
                return index
            elapsed += clip_duration
        return len(clips)


class FilmAssembler:
    """Combine shot-level clips into a long-form film."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def assemble(
        self,
        scenes: Sequence[ScenePlan],
        output_path: Path,
        shot_video_map: Mapping[str, Path],
    ) -> Path:
        clips = []
        for scene in scenes:
            for shot in scene.shots:
                video_path = shot_video_map.get(shot.name)
                if not video_path:
                    raise FileNotFoundError(f"Missing rendered video for shot '{shot.name}'")
                self._logger.debug("Appending rendered shot %s", video_path)
                clip = VideoFileClip(str(video_path))
                clips.append(clip)

        final_clip = concatenate_videoclips(clips, method="compose")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            final_clip.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                remove_temp=True,
                verbose=False,
                logger=None,
            )
        finally:
            final_clip.close()
            for clip in clips:
                if hasattr(clip, "close"):
                    clip.close()
        return output_path


class KenBurnsFilmBuilder:
    """High-level coordinator that renders narration, Ken Burns clips, and the final film."""

    def __init__(self, media_root: Path, logger: logging.Logger | None = None) -> None:
        self.media_root = media_root
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.tts = TTSAudioAssembler(self.logger)
        self.renderer = KenBurnsRenderer(logger=self.logger)
        self.assembler = FilmAssembler(self.logger)

    def build(
        self,
        scenes: Sequence[ScenePlan],
        image_assets: Mapping[str, str],
        supplemental_clips: Mapping[str, Sequence[VideoClipReference]] | None = None,
        film_name: str = "ken_burns_feature.mp4",
    ) -> MutableMapping[str, Path]:
        supplemental_clips = supplemental_clips or {}
        shot_video_map: dict[str, Path] = {}

        for scene in scenes:
            for shot in scene.shots:
                shot_dir = self.media_root / "shots" / shot.name.replace(" ", "_")
                if shot.tts_chunks:
                    self.logger.debug("Synthesising audio for shot %s", shot.name)
                    self.tts.synthesise_shot(shot, shot_dir / "audio")
                if shot.audio_track is None:
                    raise ValueError(f"Shot '{shot.name}' lacks an audio track plan")

                clip_references = supplemental_clips.get(shot.name, [])
                self.logger.debug("Rendering Ken Burns clip for %s", shot.name)
                video_path = self.renderer.render_shot(
                    shot,
                    image_assets=image_assets,
                    output_dir=shot_dir / "video",
                    supplemental_clips=clip_references,
                )
                shot_video_map[shot.name] = video_path

        film_path = self.media_root / film_name
        self.logger.debug("Assembling final film %s", film_path)
        self.assembler.assemble(scenes, film_path, shot_video_map)
        return {"film": film_path, "shots": shot_video_map}
