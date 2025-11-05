const formElements = {
  input: document.getElementById("story-input"),
  button: document.getElementById("generate-btn"),
  status: document.getElementById("status-message"),
  resultsPanel: document.getElementById("results"),
  sceneList: document.getElementById("scene-list"),
};

const API_URL = (() => {
  const { protocol, host } = window.location;
  if (protocol.startsWith("http") && host) {
    return `${window.location.origin.replace(/\/$/, "")}/api/scripts/generate`;
  }
  return "http://localhost:8000/api/scripts/generate";
})();

async function handleGenerate() {
  const storyText = formElements.input.value.trim();

  if (!storyText) {
    formElements.status.textContent = "Please enter a story before generating.";
    formElements.input.focus();
    return;
  }

  toggleLoading(true);
  try {
    const response = await fetch(API_URL, {
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
    formElements.status.textContent = `Generated ${data.scenes.length} scene(s).`;
  } catch (error) {
    console.error(error);
    formElements.status.textContent = error.message || "Unexpected error occurred.";
    formElements.resultsPanel.hidden = true;
  } finally {
    toggleLoading(false);
  }
}

function toggleLoading(isLoading) {
  formElements.button.disabled = isLoading;
  formElements.button.textContent = isLoading ? "Generating..." : "Generate Script";
  formElements.status.textContent = isLoading ? "Generating scene plan..." : formElements.status.textContent;
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
        assetHeader.textContent = "Assets:";
        shotItem.appendChild(assetHeader);

        const assetList = document.createElement("ul");
        assetList.className = "asset-list";

        shot.assets.forEach((asset) => {
          const assetItem = document.createElement("li");
          assetItem.textContent = `${asset.asset_type}: ${asset.description}`;
          assetList.appendChild(assetItem);
        });

        shotItem.appendChild(assetList);
      }

      shotList.appendChild(shotItem);
    });

    card.appendChild(header);
    card.appendChild(shotList);
    formElements.sceneList.appendChild(card);
  });

  formElements.resultsPanel.hidden = false;
}

formElements.button.addEventListener("click", handleGenerate);

formElements.input.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "enter") {
    event.preventDefault();
    handleGenerate();
  }
});
