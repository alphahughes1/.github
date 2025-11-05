"""FastAPI backend powering the short-film script generator."""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pipeline import StoryPipelineController
from pipeline.models import ScenePlan, ShotPlan, AssetPlan

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
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, model: AssetPlan) -> "AssetPlanResponse":
        return cls(**asdict(model))


class ShotPlanResponse(BaseModel):
    name: str
    clip_duration: float
    visual_prompt: str
    narration_text: str
    notes: str | None = None
    assets: List[AssetPlanResponse] = Field(default_factory=list)

    @classmethod
    def from_model(cls, model: ShotPlan) -> "ShotPlanResponse":
        return cls(
            name=model.name,
            clip_duration=model.clip_duration,
            visual_prompt=model.visual_prompt,
            narration_text=model.narration_text,
            notes=model.notes,
            assets=[AssetPlanResponse.from_model(asset) for asset in model.assets],
        )


class ScenePlanResponse(BaseModel):
    name: str
    summary: str
    metadata: dict[str, str] = Field(default_factory=dict)
    shots: List[ShotPlanResponse] = Field(default_factory=list)
    background_audio: AssetPlanResponse | None = None

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
        )


class GenerateScriptResponse(BaseModel):
    scenes: List[ScenePlanResponse]


controller = StoryPipelineController(logger=logger)


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
