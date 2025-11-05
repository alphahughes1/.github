const formElements = {
  input: document.getElementById("story-input"),
  generateButton: document.getElementById("generate-btn"),
  renderButton: document.getElementById("render-btn"),
  status: document.getElementById("status-message"),
  filmStatus: document.getElementById("film-status"),
  resultsPanel: document.getElementById("results"),
  sceneList: document.getElementById("scene-list"),
  filmOutput: document.getElementById("film-output"),
  filmPath: document.querySelector("#film-output .film-path"),
  shotOutputList: document.querySelector("#film-output .shot-output-list"),
  voiceInput: document.getElementById("voice-input"),
  filmName: document.getElementById("film-name"),
  imageAssets: document.getElementById("image-assets-input"),
  clipInput: document.getElementById("clip-input"),
};

const API_BASE = (() => {
  const { protocol, host } = window.location;
  if (protocol.startsWith("http") && host) {
    return window.location.origin.replace(/\/$/, "");
  }
  return "http://localhost:8000";
})();

const ENDPOINTS = {
  plan: `${API_BASE}/api/scripts/generate`,
  render: `${API_BASE}/api/films/render`,
};

async function handleGenerate() {
  const storyText = formElements.input.value.trim();

  if (!storyText) {
    formElements.status.textContent = "Please enter a story before generating.";
    formElements.input.focus();
    return;
  }

  setButtonLoading(formElements.generateButton, true, "Generating...");
  try {
    const response = await fetch(ENDPOINTS.plan, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ story_text: storyText }),
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      const message = errorPayload.detail || "Failed to generate script.";
      throw new Error(message);
    }

    const data = await response.json();
    renderScenes(data.scenes);
    formElements.filmOutput.hidden = true;
    formElements.filmStatus.textContent = "";
    formElements.status.textContent = `Generated ${data.scenes.length} scene(s).`;
  } catch (error) {
    console.error(error);
    formElements.status.textContent = error.message || "Unexpected error occurred.";
    formElements.resultsPanel.hidden = true;
  } finally {
    setButtonLoading(formElements.generateButton, false, "Generate Plan");
  }
}

function setButtonLoading(button, isLoading, loadingText) {
  const defaultText = button.dataset.defaultText || button.textContent;
  if (!button.dataset.defaultText) {
    button.dataset.defaultText = defaultText;
  }
  button.disabled = isLoading;
  button.textContent = isLoading ? loadingText : button.dataset.defaultText;
}

function renderScenes(scenes) {
  if (!Array.isArray(scenes) || scenes.length === 0) {
    formElements.status.textContent = "No scenes were generated.";
    formElements.resultsPanel.hidden = true;
    return;
  }

  formElements.sceneList.innerHTML = "";
  scenes.forEach((scene, index) => {
    const card = document.createElement("article");
    card.className = "scene-card";

    const header = document.createElement("div");
    header.className = "scene-header";

    const title = document.createElement("h3");
    title.textContent = `${scene.name || `Scene ${index + 1}`}`;

    const summary = document.createElement("p");
    summary.textContent = scene.summary;

    header.appendChild(title);
    header.appendChild(summary);

    const shotList = document.createElement("ul");
    shotList.className = "shot-list";

    (scene.shots || []).forEach((shot) => {
      const shotItem = document.createElement("li");
      shotItem.className = "shot-item";

      const shotTitle = document.createElement("strong");
      shotTitle.textContent = `${shot.name} · ${shot.clip_duration.toFixed(1)}s`;

      const prompt = document.createElement("p");
      prompt.textContent = shot.visual_prompt;

      const narration = document.createElement("p");
      narration.textContent = `Narration: ${shot.narration_text}`;

      shotItem.appendChild(shotTitle);
      shotItem.appendChild(prompt);
      shotItem.appendChild(narration);

      if (Array.isArray(shot.assets) && shot.assets.length > 0) {
        const assetHeader = document.createElement("p");
        assetHeader.className = "subsection-title";
        assetHeader.textContent = "Assets";
        shotItem.appendChild(assetHeader);

        const assetList = document.createElement("ul");
        assetList.className = "asset-list";

        shot.assets.forEach((asset) => {
          const assetItem = document.createElement("li");
          const parts = [asset.asset_type, asset.description]
            .filter(Boolean)
            .join(": ");
          const timing = formatTiming(asset.start_time, asset.end_time, asset.duration);
          assetItem.textContent = timing ? `${parts} (${timing})` : parts;
          assetList.appendChild(assetItem);
        });

        shotItem.appendChild(assetList);
      }

      if (Array.isArray(shot.tts_chunks) && shot.tts_chunks.length > 0) {
        const ttsHeader = document.createElement("p");
        ttsHeader.className = "subsection-title";
        ttsHeader.textContent = "Narration Chunks";
        shotItem.appendChild(ttsHeader);

        const ttsList = document.createElement("ul");
        ttsList.className = "asset-list";
        shot.tts_chunks.forEach((chunk) => {
          const chunkItem = document.createElement("li");
          chunkItem.textContent = `#${chunk.chunk_index} · ${chunk.duration.toFixed(
            1
          )}s — ${chunk.text}`;
          ttsList.appendChild(chunkItem);
        });
        shotItem.appendChild(ttsList);
      }

      if (Array.isArray(shot.ken_burns_segments) && shot.ken_burns_segments.length > 0) {
        const kbHeader = document.createElement("p");
        kbHeader.className = "subsection-title";
        kbHeader.textContent = "Ken Burns Segments";
        shotItem.appendChild(kbHeader);

        const kbList = document.createElement("ul");
        kbList.className = "asset-list";
        shot.ken_burns_segments.forEach((segment) => {
          const segmentItem = document.createElement("li");
          segmentItem.textContent = `${segment.identifier} · ${segment.duration.toFixed(
            1
          )}s (${segment.pan_direction})`;
          kbList.appendChild(segmentItem);
        });
        shotItem.appendChild(kbList);
      }

      if (Array.isArray(shot.inserted_clips) && shot.inserted_clips.length > 0) {
        const clipHeader = document.createElement("p");
        clipHeader.className = "subsection-title";
        clipHeader.textContent = "Supplemental Clips";
        shotItem.appendChild(clipHeader);

        const clipList = document.createElement("ul");
        clipList.className = "asset-list";
        shot.inserted_clips.forEach((clip) => {
          const clipItem = document.createElement("li");
          const description = clip.description ? ` — ${clip.description}` : "";
          clipItem.textContent = `${clip.source_uri} · ${clip.duration.toFixed(1)}s${description}`;
          clipList.appendChild(clipItem);
        });
        shotItem.appendChild(clipList);
      }

      if (shot.audio_track) {
        const audioInfo = document.createElement("p");
        audioInfo.className = "subsection-title";
        audioInfo.textContent = "Audio Track";
        shotItem.appendChild(audioInfo);

        const audioDetails = document.createElement("p");
        const duration = shot.audio_track.duration
          ? `${shot.audio_track.duration.toFixed(1)}s`
          : "unknown length";
        audioDetails.textContent = `${shot.audio_track.identifier} (${duration})`;
        shotItem.appendChild(audioDetails);
      }

      if (shot.assembled_video) {
        const videoInfo = document.createElement("p");
        videoInfo.className = "subsection-title";
        videoInfo.textContent = "Rendered Clip";
        shotItem.appendChild(videoInfo);

        const videoDetails = document.createElement("p");
        videoDetails.textContent = `${shot.assembled_video.identifier} (${shot.clip_duration.toFixed(
          1
        )}s)`;
        shotItem.appendChild(videoDetails);
      }

      shotList.appendChild(shotItem);
    });

    card.appendChild(header);
    card.appendChild(shotList);
    formElements.sceneList.appendChild(card);
  });

  formElements.resultsPanel.hidden = false;
}

function formatTiming(start, end, duration) {
  if (typeof duration === "number") {
    return `${duration.toFixed(1)}s`;
  }
  if (typeof start === "number" && typeof end === "number") {
    return `${start.toFixed(1)}s → ${end.toFixed(1)}s`;
  }
  return "";
}

function parseImageAssets(text) {
  const entries = [];
  text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line) => {
      const [key, value] = line.split("=");
      if (!key || !value) {
        throw new Error(`Invalid image asset entry: ${line}`);
      }
      entries.push({ asset_identifier: key.trim(), path: value.trim() });
    });
  return entries;
}

function parseSupplementalClips(text) {
  const entries = [];
  text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line) => {
      const [shotName, payload] = line.split("=");
      if (!shotName || !payload) {
        throw new Error(`Invalid supplemental clip entry: ${line}`);
      }
      const parts = payload.split(",").map((part) => part.trim());
      const [path, durationRaw, offsetRaw, ...descriptionParts] = parts;
      if (!path || !durationRaw) {
        throw new Error(`Supplemental clip requires a path and duration: ${line}`);
      }
      const duration = Number.parseFloat(durationRaw);
      if (Number.isNaN(duration) || duration <= 0) {
        throw new Error(`Invalid clip duration: ${durationRaw}`);
      }
      const insertionOffset = offsetRaw ? Number.parseFloat(offsetRaw) : 0;
      const description = descriptionParts.join(", ");
      entries.push({
        shot_name: shotName.trim(),
        source_uri: path,
        duration,
        insertion_offset: Number.isNaN(insertionOffset) ? 0 : insertionOffset,
        description,
      });
    });
  return entries;
}

async function handleRender() {
  const storyText = formElements.input.value.trim();
  if (!storyText) {
    formElements.status.textContent = "Please enter a story before rendering.";
    formElements.input.focus();
    return;
  }

  let imageAssets;
  let supplementalClips;
  try {
    imageAssets = parseImageAssets(formElements.imageAssets.value);
    if (!imageAssets.length) {
      throw new Error("Please provide at least one image asset mapping.");
    }
    supplementalClips = parseSupplementalClips(formElements.clipInput.value);
  } catch (error) {
    formElements.filmStatus.textContent = error.message;
    return;
  }

  const payload = {
    story_text: storyText,
    voice: formElements.voiceInput.value.trim() || undefined,
    film_name: formElements.filmName.value.trim() || undefined,
    image_assets: imageAssets,
    supplemental_clips: supplementalClips,
  };

  formElements.filmStatus.textContent = "Rendering film...";
  setButtonLoading(formElements.renderButton, true, "Rendering...");

  try {
    const response = await fetch(ENDPOINTS.render, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      const message = errorPayload.detail || "Failed to render film.";
      throw new Error(message);
    }

    const data = await response.json();
    renderScenes(data.plan.scenes);
    renderFilmOutputs(data.film_path, data.shots);
    formElements.filmStatus.textContent = "Film rendered successfully.";
  } catch (error) {
    console.error(error);
    formElements.filmStatus.textContent = error.message || "Unexpected render error.";
    formElements.filmOutput.hidden = true;
  } finally {
    setButtonLoading(formElements.renderButton, false, "Render Film");
  }
}

function renderFilmOutputs(filmPath, shotPaths) {
  if (!filmPath) {
    formElements.filmOutput.hidden = true;
    return;
  }
  formElements.filmPath.textContent = `Final film: ${filmPath}`;
  formElements.shotOutputList.innerHTML = "";
  Object.entries(shotPaths || {}).forEach(([shotName, path]) => {
    const item = document.createElement("li");
    item.textContent = `${shotName}: ${path}`;
    formElements.shotOutputList.appendChild(item);
  });
  formElements.filmOutput.hidden = false;
}

formElements.generateButton.addEventListener("click", handleGenerate);
formElements.renderButton.addEventListener("click", handleRender);

formElements.input.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "enter") {
    event.preventDefault();
    handleGenerate();
  }
});
