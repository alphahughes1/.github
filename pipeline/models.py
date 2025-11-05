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
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ShotPlan:
    """Structured plan for a single shot within a scene."""

    name: str
    clip_duration: float
    visual_prompt: str
    narration_text: str
    assets: List[AssetPlan] = field(default_factory=list)
    notes: Optional[str] = None

    def add_asset(self, asset: AssetPlan) -> None:
        """Attach an asset to the shot."""
        self.assets.append(asset)


@dataclass(slots=True)
class ScenePlan:
    """High-level plan covering a portion of the story."""

    name: str
    summary: str
    shots: List[ShotPlan] = field(default_factory=list)
    background_audio: Optional[AssetPlan] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def add_shot(self, shot: ShotPlan) -> None:
        """Append a new shot to the scene."""
        self.shots.append(shot)
