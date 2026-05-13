let currentBlob = null;
let currentUrl = null;

function timestamp() {
  const d = new Date();
  const pad = (n) => n.toString().padStart(2, "0");
  return (
    d.getFullYear() +
    pad(d.getMonth() + 1) +
    pad(d.getDate()) +
    "-" +
    pad(d.getHours()) +
    pad(d.getMinutes()) +
    pad(d.getSeconds())
  );
}

export function showPreview(modalEl, imgEl, blob) {
  if (currentUrl) URL.revokeObjectURL(currentUrl);
  currentBlob = blob;
  currentUrl = URL.createObjectURL(blob);
  imgEl.src = currentUrl;
  modalEl.hidden = false;
}

export function closePreview(modalEl) {
  modalEl.hidden = true;
}

export function downloadCurrent() {
  if (!currentBlob || !currentUrl) return;
  const a = document.createElement("a");
  a.href = currentUrl;
  a.download = `selfie-${timestamp()}.jpg`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// TODO: replace with local print agent when the small printer is connected
// (POST currentBlob to a local Node service that uses CUPS/`lp`).
export function printCurrent() {
  if (!currentUrl) return;
  const w = window.open("", "_blank");
  if (!w) {
    window.print();
    return;
  }
  w.document.write(`
    <html><head><title>列印</title>
    <style>
      body { margin: 0; display: flex; align-items: center; justify-content: center; }
      img { max-width: 100%; max-height: 100vh; }
      @media print { @page { margin: 0; } body { padding: 0; } }
    </style>
    </head><body><img src="${currentUrl}" onload="window.focus();window.print();" /></body></html>
  `);
  w.document.close();
}
