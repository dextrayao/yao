import { captureFrame } from "./capture.js";
import { runCountdown } from "./countdown.js";

function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function loadBlob(blob) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = reject;
    img.src = url;
  });
}

// Take 4 photos in sequence and tile them into a single 2x2 collage with a
// header showing the date.
export async function captureStrip({ videoEl, viewportEl, countdownEl, flashEl }) {
  const shots = [];
  for (let i = 0; i < 4; i++) {
    await runCountdown(countdownEl, flashEl, 3);
    const { blob } = await captureFrame(videoEl, viewportEl);
    shots.push(blob);
    await wait(400);
  }

  const images = await Promise.all(shots.map(loadBlob));

  const tileW = images[0].width;
  const tileH = images[0].height;
  const gap = 24;
  const header = 100;
  const padding = 32;
  const cols = 2;
  const rows = 2;
  const totalW = padding * 2 + tileW * cols + gap * (cols - 1);
  const totalH = padding * 2 + header + tileH * rows + gap * (rows - 1);

  const canvas = document.createElement("canvas");
  canvas.width = totalW;
  canvas.height = totalH;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "#fff8f0";
  ctx.fillRect(0, 0, totalW, totalH);

  ctx.fillStyle = "#ff4d6d";
  ctx.font = `bold ${Math.round(header * 0.6)}px -apple-system, "PingFang TC", sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const now = new Date();
  const stamp = `Selfie Booth · ${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  ctx.fillText(stamp, totalW / 2, padding + header / 2);

  images.forEach((img, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = padding + col * (tileW + gap);
    const y = padding + header + row * (tileH + gap);
    ctx.drawImage(img, x, y, tileW, tileH);
    ctx.strokeStyle = "#ff4d6d";
    ctx.lineWidth = 6;
    ctx.strokeRect(x, y, tileW, tileH);
  });

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve({ blob, width: totalW, height: totalH }), "image/jpeg", 0.92);
  });
}

function pad(n) {
  return n.toString().padStart(2, "0");
}
