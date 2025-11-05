# Short Film Script Generator

This project combines a Python backend and a lightweight frontend to turn raw story ideas into structured short-film production plans that are ready to hand off to YouTube content pipelines.

## Project Structure

- `pipeline/` – data models, scene planning logic, the pipeline scheduler, and Ken Burns production helpers.
- `backend/` – FastAPI application exposing HTTP endpoints for generating scripts.
- `frontend/` – static web experience that interacts with the backend and renders scene plans.
- `requirements.txt` – Python dependencies for running the backend.

## Getting Started

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\\Scripts\\activate
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

> **Tip:** Rendering video and audio relies on `moviepy`, `pyttsx3`, and `pydub`. Ensure `ffmpeg` is available on your system and, on Linux, install a speech synthesis engine such as `espeak` for `pyttsx3` to synthesise narration.

### 3. Run the FastAPI server

```bash
uvicorn backend.app:app --reload
```

The server listens on `http://127.0.0.1:8000` by default and exposes:

- `GET /health` – quick health probe endpoint.
- `POST /api/scripts/generate` – accepts `{ "story_text": "..." }` and returns the generated scene plan.
- `POST /api/films/render` – accepts a story, generated image paths, and optional supplemental clip metadata and produces a narrated Ken Burns film on disk.

The render endpoint payload uses the following structure:

```jsonc
{
  "story_text": "...",
  "voice": "com.apple.speech.synthesis.voice.samantha",   // optional
  "film_name": "ken_burns_feature.mp4",                    // optional
  "image_assets": [
    { "asset_identifier": "Shot 1.1-visual", "path": "/abs/path/shot_1_1.png" }
  ],
  "supplemental_clips": [
    {
      "shot_name": "Shot 2.1",
      "source_uri": "/abs/path/cutaway.mp4",
      "duration": 6.0,
      "insertion_offset": 3.0,
      "description": "B-roll of the city skyline"
    }
  ]
}
```

### 4. Launch the frontend

Serve the `frontend/` directory with any static file server. For example:

```bash
python -m http.server --directory frontend 5173
```

Navigate to `http://127.0.0.1:5173` in your browser and connect to the backend at `http://127.0.0.1:8000`.

### Rendering a Ken Burns style film locally

1. Generate still imagery for each `image_prompt` asset (e.g., using a diffusion model) and note the file paths.
2. Add optional short-form videos you want stitched into specific shots.
3. Paste the story, image asset mappings, and supplemental clip metadata into the frontend or call `POST /api/films/render` manually.
4. The backend will synthesise narration, pan/zoom across each still using the Ken Burns effect, blend in any provided clips, and assemble a seamless 20–30 minute feature-length MP4 with narration.

Image mappings must follow `asset_id=/abs/path/to/image.png` (one per line). Supplemental clips use `Shot Name=/abs/path.mp4,duration_seconds,insertion_offset,optional description`.

Generated media is stored under `media/` by default. The response payload also reports the final film path and every per-shot render.

### Running the planner without the web UI

You can execute the core planner and scheduler directly:

```bash
python - <<'PY'
from pipeline import StoryPipelineController

story = """A group of friends find a mysterious key.
They discover it unlocks a hidden studio where music comes alive.
They decide to stream their performances and become an overnight sensation."""

controller = StoryPipelineController()
scenes = controller.plan_and_schedule(story)
for scene in scenes:
    print(scene.name, "-", scene.summary)
    for shot in scene.shots:
        print("  ", shot.name, shot.clip_duration, shot.visual_prompt)
PY
```

## Frontend Preview

The frontend now includes two workflows:

- **Generate Plan** – produce a detailed scene plan with narration chunks, Ken Burns segments, and external asset requirements.
- **Render Film** – submit story, voice, image asset mappings, and optional supplemental clips to create narrated Ken Burns videos and a stitched long-form film. Render results list the final film path and each per-shot video output.

Use CMD/CTRL + Enter inside the story textarea as a shortcut to trigger plan generation.
