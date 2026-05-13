let audioCtx = null;

function playShutter() {
  if (!audioCtx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    audioCtx = new AC();
  }
  const ctx = audioCtx;
  const now = ctx.currentTime;

  // Click: short high-pass burst of noise
  const buf = ctx.createBuffer(1, ctx.sampleRate * 0.08, ctx.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < data.length; i++) {
    data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / data.length, 2);
  }
  const noise = ctx.createBufferSource();
  noise.buffer = buf;
  const hp = ctx.createBiquadFilter();
  hp.type = "highpass";
  hp.frequency.value = 1800;
  const gain = ctx.createGain();
  gain.gain.value = 0.4;
  noise.connect(hp).connect(gain).connect(ctx.destination);
  noise.start(now);

  // Mechanical thunk: short low sine
  const osc = ctx.createOscillator();
  osc.type = "sine";
  osc.frequency.setValueAtTime(220, now);
  osc.frequency.exponentialRampToValueAtTime(80, now + 0.08);
  const og = ctx.createGain();
  og.gain.setValueAtTime(0.5, now);
  og.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
  osc.connect(og).connect(ctx.destination);
  osc.start(now);
  osc.stop(now + 0.12);
}

function playTick() {
  if (!audioCtx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    audioCtx = new AC();
  }
  const ctx = audioCtx;
  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  osc.type = "sine";
  osc.frequency.value = 880;
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.2, now);
  g.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
  osc.connect(g).connect(ctx.destination);
  osc.start(now);
  osc.stop(now + 0.1);
}

function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function runCountdown(countdownEl, flashEl, seconds = 3) {
  for (let n = seconds; n >= 1; n--) {
    countdownEl.textContent = String(n);
    countdownEl.classList.remove("active");
    // Force reflow so the animation restarts each digit.
    void countdownEl.offsetWidth;
    countdownEl.classList.add("active");
    playTick();
    await wait(900);
  }
  countdownEl.classList.remove("active");
  countdownEl.textContent = "";

  flashEl.classList.remove("fire");
  void flashEl.offsetWidth;
  flashEl.classList.add("fire");
  playShutter();
  await wait(180);
}
