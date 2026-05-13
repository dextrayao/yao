import { loadManifest } from "./stickers.js";

let activeFrame = { id: "none", name: "無邊框", file: null };
const cache = new Map();

export function getActiveFrame() {
  return activeFrame;
}

export function loadFrameImage(frame) {
  if (cache.has(frame.id)) return cache.get(frame.id);
  const p = new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = frame.file;
  });
  cache.set(frame.id, p);
  return p;
}

export async function renderFrameChips(containerEl, frameOverlayEl) {
  const m = await loadManifest();
  containerEl.innerHTML = "";
  m.frames.forEach((f) => {
    const chip = document.createElement("button");
    chip.className = "chip" + (f.id === activeFrame.id ? " active" : "");
    chip.dataset.id = f.id;
    chip.textContent = f.name;
    chip.onclick = () => {
      activeFrame = f;
      frameOverlayEl.style.backgroundImage = f.file ? `url(${f.file})` : "none";
      containerEl.querySelectorAll(".chip").forEach((c) => {
        c.classList.toggle("active", c.dataset.id === f.id);
      });
    };
    containerEl.appendChild(chip);
  });
}
