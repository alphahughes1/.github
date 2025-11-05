"""FastAPI backend powering the short-film script generator."""
from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pipeline import StoryPipelineController
from pipeline.models import (
    AssetPlan,
    KenBurnsSegment,
    ScenePlan,
    ShotPlan,
    TTSChunk,
    VideoClipReference,
)
from pipeline.production import KenBurnsFilmBuilder

logger = logging.getLogger("backend")

app = FastAPI(title="Short Film Script Generator", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateScriptRequest(BaseModel):
    story_text: str = Field(..., description="Narrative text describing the story")


class AssetPlanResponse(BaseModel):
    identifier: str
    asset_type: str
    description: str
    source_uri: str | None = None
    duration: float | None = None
    start_time: float | None = None
    end_time: float | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, model: AssetPlan) -> "AssetPlanResponse":
        return cls(**asdict(model))


class TTSChunkResponse(BaseModel):
    identifier: str
    text: str
    chunk_index: int
    start_offset: float
    duration: float
    voice: str

    @classmethod
    def from_model(cls, model: TTSChunk) -> "TTSChunkResponse":
        return cls(**asdict(model))


class KenBurnsSegmentResponse(BaseModel):
    identifier: str
    asset_identifier: str
    duration: float
    zoom_start: float
    zoom_end: float
    pan_direction: str
    start_offset: float

    @classmethod
    def from_model(cls, model: KenBurnsSegment) -> "KenBurnsSegmentResponse":
        return cls(**asdict(model))


class VideoClipReferenceResponse(BaseModel):
    identifier: str
    source_uri: str
    duration: float
    insertion_offset: float
    description: str

    @classmethod
    def from_model(cls, model: VideoClipReference) -> "VideoClipReferenceResponse":
        return cls(**asdict(model))


class ShotPlanResponse(BaseModel):
    name: str
    clip_duration: float
    visual_prompt: str
    narration_text: str
    notes: str | None = None
    assets: List[AssetPlanResponse] = Field(default_factory=list)
    tts_chunks: List[TTSChunkResponse] = Field(default_factory=list)
    ken_burns_segments: List[KenBurnsSegmentResponse] = Field(default_factory=list)
    inserted_clips: List[VideoClipReferenceResponse] = Field(default_factory=list)
    audio_track: AssetPlanResponse | None = None
    assembled_video: AssetPlanResponse | None = None

    @classmethod
    def from_model(cls, model: ShotPlan) -> "ShotPlanResponse":
        return cls(
            name=model.name,
            clip_duration=model.clip_duration,
            visual_prompt=model.visual_prompt,
            narration_text=model.narration_text,
            notes=model.notes,
            assets=[AssetPlanResponse.from_model(asset) for asset in model.assets],
            tts_chunks=[TTSChunkResponse.from_model(chunk) for chunk in model.tts_chunks],
            ken_burns_segments=[
                KenBurnsSegmentResponse.from_model(segment)
                for segment in model.ken_burns_segments
            ],
            inserted_clips=[
                VideoClipReferenceResponse.from_model(clip)
                for clip in model.inserted_clips
            ],
            audio_track=(
                AssetPlanResponse.from_model(model.audio_track)
                if model.audio_track
                else None
            ),
            assembled_video=(
                AssetPlanResponse.from_model(model.assembled_video)
                if model.assembled_video
                else None
            ),
        )


class ScenePlanResponse(BaseModel):
    name: str
    summary: str
    metadata: dict[str, str] = Field(default_factory=dict)
    shots: List[ShotPlanResponse] = Field(default_factory=list)
    background_audio: AssetPlanResponse | None = None
    total_duration: float | None = None

    @classmethod
    def from_model(cls, model: ScenePlan) -> "ScenePlanResponse":
        background_audio = (
            AssetPlanResponse.from_model(model.background_audio)
            if model.background_audio
            else None
        )
        return cls(
            name=model.name,
            summary=model.summary,
            metadata=model.metadata,
            shots=[ShotPlanResponse.from_model(shot) for shot in model.shots],
            background_audio=background_audio,
            total_duration=model.total_duration,
        )


class GenerateScriptResponse(BaseModel):
    scenes: List[ScenePlanResponse]


controller = StoryPipelineController(logger=logger)
media_builder = KenBurnsFilmBuilder(media_root=Path("media"), logger=logger)


class ImageAssetInput(BaseModel):
    asset_identifier: str
    path: str


class SupplementalClipInput(BaseModel):
    shot_name: str
    source_uri: str
    duration: float = Field(..., gt=0)
    insertion_offset: float = Field(0.0, ge=0)
    description: str = ""


class RenderFilmRequest(BaseModel):
    story_text: str
    image_assets: List[ImageAssetInput]
    supplemental_clips: List[SupplementalClipInput] = Field(default_factory=list)
    voice: str | None = None
    film_name: str | None = None


class RenderFilmResponse(BaseModel):
    film_path: str
    shots: Dict[str, str]
    plan: GenerateScriptResponse


def _group_supplemental_clips(
    inputs: List[SupplementalClipInput],
) -> Dict[str, List[VideoClipReference]]:
    grouped: Dict[str, List[VideoClipReference]] = {}
    counters: Dict[str, int] = {}
    for clip in inputs:
        counters.setdefault(clip.shot_name, 0)
        counters[clip.shot_name] += 1
        identifier = f"{clip.shot_name}-supplemental-{counters[clip.shot_name]}"
        grouped.setdefault(clip.shot_name, []).append(
            VideoClipReference(
                identifier=identifier,
                source_uri=clip.source_uri,
                duration=clip.duration,
                insertion_offset=clip.insertion_offset,
                description=clip.description,
            )
        )
    return grouped


@app.get("/health")
def health_check() -> dict[str, str]:
    """Lightweight endpoint for health probes."""
    return {"status": "ok"}


@app.post("/api/scripts/generate", response_model=GenerateScriptResponse)
def generate_script(payload: GenerateScriptRequest) -> GenerateScriptResponse:
    story_text = payload.story_text.strip()
    if not story_text:
        raise HTTPException(status_code=400, detail="story_text must not be empty")

    scenes = controller.plan_and_schedule(story_text)
    response_scenes = [ScenePlanResponse.from_model(scene) for scene in scenes]
    return GenerateScriptResponse(scenes=response_scenes)


@app.post("/api/films/render", response_model=RenderFilmResponse)
def render_film(payload: RenderFilmRequest) -> RenderFilmResponse:
    story_text = payload.story_text.strip()
    if not story_text:
        raise HTTPException(status_code=400, detail="story_text must not be empty")
    if not payload.image_assets:
        raise HTTPException(status_code=400, detail="image_assets must not be empty")

    image_assets: Dict[str, str] = {}
    for asset in payload.image_assets:
        asset_path = Path(asset.path)
        if not asset_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Image asset '{asset.path}' could not be found",
            )
        image_assets[asset.asset_identifier] = str(asset_path)

    clip_inputs = _group_supplemental_clips(payload.supplemental_clips)

    original_voice = controller.default_voice
    if payload.voice:
        controller.default_voice = payload.voice

    try:
        scenes = controller.plan_and_schedule(story_text, inserted_clips=clip_inputs)
    finally:
        controller.default_voice = original_voice

    plan_response = GenerateScriptResponse(
        scenes=[ScenePlanResponse.from_model(scene) for scene in scenes]
    )

    supplemental_map: Dict[str, List[VideoClipReference]] = {}
    for scene in scenes:
        for shot in scene.shots:
            if shot.inserted_clips:
                supplemental_map[shot.name] = shot.inserted_clips

    try:
        film_outputs = media_builder.build(
            scenes,
            image_assets=image_assets,
            supplemental_clips=supplemental_map,
            film_name=payload.film_name or "ken_burns_feature.mp4",
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        logger.exception("Failed to render film")
        raise HTTPException(status_code=500, detail="Failed to render film") from exc

    film_path = film_outputs["film"]
    shot_paths = {
        shot_name: str(path)
        for shot_name, path in film_outputs["shots"].items()
    }

    return RenderFilmResponse(
        film_path=str(film_path),
        shots=shot_paths,
        plan=plan_response,
    )
