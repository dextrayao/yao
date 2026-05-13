import { getActiveFilter } from "./filters.js";
import { getStickers } from "./stickers.js";
import { getActiveFrame, loadFrameImage } from "./frames.js";

// Capture a single still from <video> with current filter, stickers, and frame
// composited. The result respects the mirrored selfie preview so what users see
// is what they get.
export async function captureFrame(videoEl, viewportEl) {
  const w = videoEl.videoWidth || 1280;
  const h = videoEl.videoHeight || 720;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");

  // Mirror to match preview
  ctx.save();
  ctx.translate(w, 0);
  ctx.scale(-1, 1);
  ctx.filter = getActiveFilter().css;
  ctx.drawImage(videoEl, 0, 0, w, h);
  ctx.restore();
  ctx.filter = "none";

  // Stickers — translate from viewport coords to video coords
  const vpRect = viewportEl.getBoundingClientRect();
  const scaleX = w / vpRect.width;
  const scaleY = h / vpRect.height;

  for (const s of getStickers()) {
    const img = await loadImage(s.src);
    const sx = s.x * scaleX;
    const sy = s.y * scaleY;
    const sw = s.width * scaleX;
    const sh = s.height * scaleY;
    ctx.drawImage(img, sx, sy, sw, sh);
  }

  // Frame
  const frame = getActiveFrame();
  if (frame && frame.file) {
    const img = await loadFrameImage(frame);
    ctx.drawImage(img, 0, 0, w, h);
  }

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve({ blob, width: w, height: h }), "image/jpeg", 0.92);
  });
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}
