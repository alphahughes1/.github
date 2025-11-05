# Short Film Script Generator

This project combines a Python backend and a lightweight frontend to turn raw story ideas into structured short-film production plans that are ready to hand off to YouTube content pipelines.

## Project Structure

- `pipeline/` – data models, scene planning logic, and the pipeline scheduler.
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

### 3. Run the FastAPI server

```bash
uvicorn backend.app:app --reload
```

The server listens on `http://127.0.0.1:8000` by default and exposes:

- `GET /health` – quick health probe endpoint.
- `POST /api/scripts/generate` – accepts `{ "story_text": "..." }` and returns the generated scene plan.

### 4. Launch the frontend

Serve the `frontend/` directory with any static file server. For example:

```bash
python -m http.server --directory frontend 5173
```

Navigate to `http://127.0.0.1:5173` in your browser and connect to the backend at `http://127.0.0.1:8000`.

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

The frontend provides a textarea for entering the story, a generate button, and a responsive results panel that lists scenes, shots, and required assets. Use CMD/CTRL + Enter inside the textarea as a shortcut to trigger generation.
