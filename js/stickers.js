let manifest = null;
let placed = []; // { id, src, x, y, width, height, el }

export async function loadManifest() {
  if (manifest) return manifest;
  const res = await fetch("assets/stickers/manifest.json");
  manifest = await res.json();
  return manifest;
}

export function getStickers() {
  return placed.map((s) => ({
    id: s.id,
    src: s.src,
    x: s.x,
    y: s.y,
    width: s.width,
    height: s.height,
  }));
}

export function clearStickers(layerEl) {
  placed.forEach((s) => s.el.remove());
  placed = [];
  if (layerEl) layerEl.innerHTML = "";
}

export function renderStickerChips(containerEl, layerEl, viewportEl) {
  loadManifest().then((m) => {
    containerEl.innerHTML = "";
    m.stickers.forEach((s) => {
      const chip = document.createElement("button");
      chip.className = "chip";
      const img = document.createElement("img");
      img.src = s.file;
      img.alt = s.name;
      chip.appendChild(img);
      chip.append(s.name);
      chip.onclick = () => addSticker(s, layerEl, viewportEl);
      containerEl.appendChild(chip);
    });
  });
}

function addSticker(stickerDef, layerEl, viewportEl) {
  const vpRect = viewportEl.getBoundingClientRect();
  const w = 140;
  const h = 140;
  const startX = (vpRect.width - w) / 2;
  const startY = (vpRect.height - h) / 2;

  const wrap = document.createElement("div");
  wrap.className = "sticker";
  wrap.style.left = `${startX}px`;
  wrap.style.top = `${startY}px`;
  wrap.style.width = `${w}px`;
  wrap.style.height = `${h}px`;

  const img = document.createElement("img");
  img.src = stickerDef.file;
  img.alt = stickerDef.name;
  img.draggable = false;
  img.style.width = "100%";
  img.style.height = "100%";
  img.style.pointerEvents = "none";
  wrap.appendChild(img);

  const remove = document.createElement("div");
  remove.className = "remove";
  remove.textContent = "×";
  remove.title = "刪除";
  wrap.appendChild(remove);

  const handle = document.createElement("div");
  handle.className = "handle";
  handle.textContent = "⤡";
  handle.title = "縮放";
  wrap.appendChild(handle);

  const record = {
    id: stickerDef.id,
    src: stickerDef.file,
    x: startX,
    y: startY,
    width: w,
    height: h,
    el: wrap,
  };
  placed.push(record);
  layerEl.appendChild(wrap);

  remove.addEventListener("pointerdown", (e) => {
    e.stopPropagation();
    placed = placed.filter((s) => s !== record);
    wrap.remove();
  });

  attachDrag(wrap, record, viewportEl);
  attachResize(handle, wrap, record, viewportEl);
}

function attachDrag(el, record, viewportEl) {
  el.addEventListener("pointerdown", (e) => {
    if (e.target.classList.contains("handle") || e.target.classList.contains("remove")) {
      return;
    }
    el.setPointerCapture(e.pointerId);
    el.classList.add("dragging");
    const startX = e.clientX;
    const startY = e.clientY;
    const origX = record.x;
    const origY = record.y;
    const vpRect = viewportEl.getBoundingClientRect();

    const onMove = (ev) => {
      let nx = origX + (ev.clientX - startX);
      let ny = origY + (ev.clientY - startY);
      nx = Math.max(-record.width / 2, Math.min(vpRect.width - record.width / 2, nx));
      ny = Math.max(-record.height / 2, Math.min(vpRect.height - record.height / 2, ny));
      record.x = nx;
      record.y = ny;
      el.style.left = `${nx}px`;
      el.style.top = `${ny}px`;
    };

    const onUp = () => {
      el.classList.remove("dragging");
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerup", onUp);
    };

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerup", onUp);
  });
}

function attachResize(handle, el, record, viewportEl) {
  handle.addEventListener("pointerdown", (e) => {
    e.stopPropagation();
    handle.setPointerCapture(e.pointerId);
    const startX = e.clientX;
    const startY = e.clientY;
    const origW = record.width;
    const origH = record.height;
    const aspect = origW / origH;

    const onMove = (ev) => {
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;
      const delta = Math.max(dx, dy);
      let newW = Math.max(40, origW + delta);
      let newH = newW / aspect;
      record.width = newW;
      record.height = newH;
      el.style.width = `${newW}px`;
      el.style.height = `${newH}px`;
    };

    const onUp = () => {
      handle.removeEventListener("pointermove", onMove);
      handle.removeEventListener("pointerup", onUp);
    };

    handle.addEventListener("pointermove", onMove);
    handle.addEventListener("pointerup", onUp);
  });
}
