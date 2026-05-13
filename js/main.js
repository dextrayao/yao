import { startCamera, populateCameraSelect } from "./camera.js";
import { renderFilterChips, getActiveFilter } from "./filters.js";
import { renderStickerChips, clearStickers } from "./stickers.js";
import { renderFrameChips } from "./frames.js";
import { runCountdown } from "./countdown.js";
import { captureFrame } from "./capture.js";
import { captureStrip } from "./photostrip.js";
import { showPreview, closePreview, downloadCurrent, printCurrent } from "./output.js";

const el = (id) => document.getElementById(id);

const video        = el("video");
const viewport     = el("viewport");
const countdownEl  = el("countdown");
const flashEl      = el("flash");
const stickerLayer = el("stickerLayer");
const frameOverlay = el("frameOverlay");
const cameraError  = el("cameraError");

const cameraSelect = el("cameraSelect");
const filterList   = el("filterList");
const stickerList  = el("stickerList");
const frameList    = el("frameList");
const clearBtn     = el("clearStickers");
const shootBtn     = el("shootBtn");

const previewModal = el("previewModal");
const previewImage = el("previewImage");
const retakeBtn    = el("retakeBtn");
const downloadBtn  = el("downloadBtn");
const printBtn     = el("printBtn");

let mode = "single"; // "single" | "strip"
let shooting = false;

async function initialize() {
  try {
    await startCamera(video);
    video.style.filter = getActiveFilter().css;
  } catch (err) {
    console.error("Camera failed to start:", err);
    cameraError.hidden = false;
    return;
  }

  await populateCameraSelect(cameraSelect, async (deviceId) => {
    try {
      await startCamera(video, deviceId);
      video.style.filter = getActiveFilter().css;
    } catch (err) {
      console.error("Camera switch failed:", err);
      cameraError.hidden = false;
    }
  });

  renderFilterChips(filterList, video);
  renderStickerChips(stickerList, stickerLayer, viewport);
  renderFrameChips(frameList, frameOverlay);

  bindModeButtons();
  bindShootButton();
  bindModalButtons();

  clearBtn.onclick = () => clearStickers(stickerLayer);
}

function bindModeButtons() {
  document.querySelectorAll(".seg").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll(".seg").forEach((b) => {
        b.classList.toggle("active", b === btn);
        b.setAttribute("aria-checked", b === btn);
      });
      mode = btn.dataset.mode;
    };
  });
}

function bindShootButton() {
  shootBtn.onclick = async () => {
    if (shooting) return;
    shooting = true;
    shootBtn.disabled = true;
    try {
      let result;
      if (mode === "strip") {
        result = await captureStrip({
          videoEl: video,
          viewportEl: viewport,
          countdownEl,
          flashEl,
        });
      } else {
        await runCountdown(countdownEl, flashEl, 3);
        result = await captureFrame(video, viewport);
      }
      showPreview(previewModal, previewImage, result.blob);
    } catch (err) {
      console.error("Shoot failed:", err);
    } finally {
      shooting = false;
      shootBtn.disabled = false;
    }
  };
}

function bindModalButtons() {
  retakeBtn.onclick = () => closePreview(previewModal);
  downloadBtn.onclick = () => downloadCurrent();
  printBtn.onclick = () => printCurrent();
}

initialize();
