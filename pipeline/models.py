"""Data models for story-driven scene planning."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class AssetPlan:
    """Description of a media asset required to realise a shot or scene."""

    identifier: str
    asset_type: str
    description: str
    source_uri: Optional[str] = None
    duration: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TTSChunk:
    """Represents a portion of narration audio to be synthesised."""

    identifier: str
    text: str
    chunk_index: int
    start_offset: float
    duration: float
    voice: str = "default"

    @property
    def end_offset(self) -> float:
        return self.start_offset + self.duration


@dataclass(slots=True)
class KenBurnsSegment:
    """Visual movement instructions for a Ken Burns style clip."""

    identifier: str
    asset_identifier: str
    duration: float
    zoom_start: float
    zoom_end: float
    pan_direction: str
    start_offset: float


@dataclass(slots=True)
class VideoClipReference:
    """Metadata describing a user-supplied or stock video clip."""

    identifier: str
    source_uri: str
    duration: float
    insertion_offset: float
    description: str = ""


@dataclass(slots=True)
class ShotPlan:
    """Structured plan for a single shot within a scene."""

    name: str
    clip_duration: float
    visual_prompt: str
    narration_text: str
    assets: List[AssetPlan] = field(default_factory=list)
    notes: Optional[str] = None
    tts_chunks: List[TTSChunk] = field(default_factory=list)
    ken_burns_segments: List[KenBurnsSegment] = field(default_factory=list)
    inserted_clips: List[VideoClipReference] = field(default_factory=list)
    audio_track: Optional[AssetPlan] = None
    assembled_video: Optional[AssetPlan] = None

    def add_asset(self, asset: AssetPlan) -> None:
        """Attach an asset to the shot."""
        self.assets.append(asset)

    def add_tts_chunk(self, chunk: TTSChunk) -> None:
        """Record a narration chunk for later synthesis."""
        self.tts_chunks.append(chunk)

    def add_ken_burns_segment(self, segment: KenBurnsSegment) -> None:
        """Store a Ken Burns movement segment for later rendering."""
        self.ken_burns_segments.append(segment)

    def add_inserted_clip(self, clip: VideoClipReference) -> None:
        """Schedule a user-supplied clip to blend into the shot."""
        self.inserted_clips.append(clip)


@dataclass(slots=True)
class ScenePlan:
    """High-level plan covering a portion of the story."""

    name: str
    summary: str
    shots: List[ShotPlan] = field(default_factory=list)
    background_audio: Optional[AssetPlan] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    total_duration: Optional[float] = None

    def add_shot(self, shot: ShotPlan) -> None:
        """Append a new shot to the scene."""
        self.shots.append(shot)
