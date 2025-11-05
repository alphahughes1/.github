# Short Film Script Generator

This project combines a Python backend and a lightweight frontend to turn raw story ideas into structured short-film production plans that are ready to hand off to YouTube content pipelines.

## Project Structure

- `pipeline/` – data models, scene planning logic, the pipeline scheduler, and Ken Burns production helpers.
- `backend/` – FastAPI application exposing HTTP endpoints for generating scripts.
- `frontend/` – static web experience that interacts with the backend and renders scene plans.
- `requirements.txt` – Python dependencies for running the backend.

The pipeline reads raw narration, splits it into scenes and shots, generates cinematic image prompts, and schedules every
downstream stage (TTS, Ken Burns motion, editing, delivery). You can feed it custom assets or rely on the built-in placeholder
generator to keep renders moving while bespoke artwork is still in progress.

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
  "image_style": "cinematic realism",                      // optional prompt styling hint
  "auto_generate_images": true,                             // optional placeholder fallback
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
3. Paste the story, image asset mappings, and supplemental clip metadata into the frontend or call `POST /api/films/render` manually. Toggle **Auto-generate cinematic placeholder images** if you want the backend to fabricate artwork for anything you did not supply yet.
4. The backend will synthesise narration, pan/zoom across each still using the Ken Burns effect, blend in any provided clips, and assemble a seamless 20–30 minute feature-length MP4 with narration. Every shot and narration chunk includes explicit start/end timestamps so you can line the film up with other editors or VFX passes.

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
- **Render Film** – submit story, voice, image asset mappings, optional supplemental clips, and optionally enable auto-generated placeholder imagery to create narrated Ken Burns videos and a stitched long-form film. Render results list the final film path, each per-shot video output, and any placeholder frames built on your behalf.

Use CMD/CTRL + Enter inside the story textarea as a shortcut to trigger plan generation.

## Running everything from a Samsung Galaxy Tab S7 (or other Android tablet)

If you only have access to a tablet, you can still run the project locally by using an Android terminal environment such as
[Termux](https://termux.dev/en/). The high-level flow looks like this:

1. **Install Termux** from F-Droid (the Play Store build is outdated). Open the app and update the package index:
   ```bash
   pkg update && pkg upgrade
   ```
2. **Install required tooling** inside Termux:
   ```bash
   pkg install git python nodejs-lts ffmpeg espeak
   pip install --upgrade pip
   ```
   > `ffmpeg` powers video assembly and `espeak` enables offline text-to-speech for `pyttsx3`.
3. **Fetch the repo** (either clone from GitHub or download the ZIP on another device and copy it over):
   ```bash
   git clone https://github.com/<your-account>/<repo-name>.git
   cd <repo-name>/.github
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Start the backend** using Uvicorn within Termux:
   ```bash
   uvicorn backend.app:app --host 0.0.0.0 --port 8000
   ```
   Leave this process running. Termux will keep it alive as long as the screen stays on; consider enabling “Wake Lock” in the
   Termux notification to prevent Android from suspending the session.
5. **Serve the frontend** from a second Termux session (swipe in from the left edge → “New session”):
   ```bash
   cd <repo-name>/.github
   source .venv/bin/activate
   python -m http.server --directory frontend 5173
   ```
6. **Open the frontend in the tablet browser** at `http://127.0.0.1:5173`. Because both servers run on the same device, the
   default configuration just works. If you see cross-origin errors, confirm the backend is still running and reachable at
   `http://127.0.0.1:8000`.

### Tips for a smoother mobile experience

- **Use an external keyboard** (Bluetooth or USB) if possible—copying scripts and editing JSON payloads is much easier.
- **Keep your tablet powered**; long renders can be CPU-intensive and may drain the battery quickly.
- **Offload heavy rendering** by pairing the frontend with a remote backend. Deploy the backend on a desktop, server, or cloud
  instance, then edit `frontend/app.js` to point `API_BASE_URL` at the remote address.
- **Monitor storage usage** under `media/`; long Ken Burns films, generated placeholder artwork, and per-shot clips can take
  several gigabytes. Periodically clean up old renders to free space.
