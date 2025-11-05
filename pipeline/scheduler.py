"""Scheduling utilities for orchestrating the media generation pipeline."""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Deque, Iterable, Optional

from .models import ScenePlan, ShotPlan


class PipelineStage(str, Enum):
    """Supported stages in the media pipeline."""

    PROMPTING = "prompting"
    MEDIA_GENERATION = "media_generation"
    AUDIO_SYNTHESIS = "audio_synthesis"
    KEN_BURNS_RENDER = "ken_burns_render"
    VIDEO_ASSEMBLY = "video_assembly"
    EDITING = "editing"
    FINAL_DELIVERY = "final_delivery"


@dataclass(slots=True)
class StageTask:
    """Represents work to be performed for a stage of a shot within a scene."""

    stage: PipelineStage
    scene: ScenePlan
    shot: Optional[ShotPlan]


class PipelineScheduler:
    """Queue-based scheduler coordinating pipeline tasks."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._queue: Deque[StageTask] = deque()

    def enqueue(self, task: StageTask) -> None:
        """Add a task to the scheduler queue."""
        self._logger.debug("Enqueuing task %s for scene=%s shot=%s", task.stage, task.scene.name, getattr(task.shot, "name", None))
        self._queue.append(task)

    def extend(self, tasks: Iterable[StageTask]) -> None:
        """Add multiple tasks to the queue."""
        for task in tasks:
            self.enqueue(task)

    def schedule_scene(self, scene: ScenePlan) -> None:
        """Generate and queue tasks for each shot in the scene."""
        if not scene.shots:
            self._logger.warning("Scene '%s' has no shots to schedule", scene.name)
            return

        for shot in scene.shots:
            for stage in PipelineStage:
                self.enqueue(StageTask(stage=stage, scene=scene, shot=shot))

    def run(self, handler: Callable[[StageTask], None]) -> None:
        """Process tasks sequentially using the provided handler."""
        while self._queue:
            task = self._queue.popleft()
            try:
                self._logger.info("Starting stage '%s' for scene='%s' shot='%s'", task.stage.value, task.scene.name, getattr(task.shot, "name", None))
                handler(task)
                self._logger.info("Completed stage '%s' for scene='%s' shot='%s'", task.stage.value, task.scene.name, getattr(task.shot, "name", None))
            except Exception:  # pragma: no cover - defensive logging
                self._logger.exception(
                    "Error while processing stage '%s' for scene='%s' shot='%s'",
                    task.stage.value,
                    task.scene.name,
                    getattr(task.shot, "name", None),
                )

    def clear(self) -> None:
        """Remove all remaining tasks from the queue."""
        self._logger.debug("Clearing %d remaining tasks", len(self._queue))
        self._queue.clear()

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._queue)
