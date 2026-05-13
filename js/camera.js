let currentStream = null;

export async function listCameras() {
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices.filter((d) => d.kind === "videoinput");
}

export async function startCamera(videoEl, deviceId) {
  stopCamera();

  const constraints = {
    audio: false,
    video: {
      width: { ideal: 1920 },
      height: { ideal: 1080 },
      facingMode: deviceId ? undefined : "user",
      deviceId: deviceId ? { exact: deviceId } : undefined,
    },
  };

  const stream = await navigator.mediaDevices.getUserMedia(constraints);
  currentStream = stream;
  videoEl.srcObject = stream;
  await videoEl.play();
  return stream;
}

export function stopCamera() {
  if (!currentStream) return;
  currentStream.getTracks().forEach((t) => t.stop());
  currentStream = null;
}

export function getCurrentStream() {
  return currentStream;
}

export async function populateCameraSelect(selectEl, onChange) {
  // First-pass enumerate may have empty labels until permission granted.
  // Caller should invoke after first startCamera() succeeds.
  const cameras = await listCameras();
  selectEl.innerHTML = "";
  cameras.forEach((cam, i) => {
    const opt = document.createElement("option");
    opt.value = cam.deviceId;
    opt.textContent = cam.label || `鏡頭 ${i + 1}`;
    selectEl.appendChild(opt);
  });

  selectEl.onchange = () => onChange(selectEl.value);
  return cameras;
}
