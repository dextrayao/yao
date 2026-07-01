// Ethereal audio, fully synthesized with WebAudio (no audio files):
// a soft ambient pad loop + gentle interaction/evolution SFX + a mute toggle.
// AudioContext is created lazily on the first user gesture (browser autoplay
// policy). Everything is quiet and calm — 空靈 ambience, not a soundtrack.

const MUTE_KEY = 'yao_muted';

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let ambientStarted = false;
let muted = localStorage.getItem(MUTE_KEY) === '1';

type Ctor = typeof AudioContext;
function getCtor(): Ctor | null {
  return (window.AudioContext ?? (window as unknown as { webkitAudioContext?: Ctor }).webkitAudioContext) ?? null;
}

/** Call on a user gesture (first tap) to unlock + start ambience. */
export function initAudio(): void {
  if (ctx) {
    void ctx.resume();
    return;
  }
  const Ctor = getCtor();
  if (!Ctor) return;
  ctx = new Ctor();
  master = ctx.createGain();
  master.gain.value = muted ? 0 : 1;
  master.connect(ctx.destination);
  startAmbient();
}

function startAmbient(): void {
  if (!ctx || !master || ambientStarted) return;
  ambientStarted = true;

  const pad = ctx.createGain();
  pad.gain.value = 0.06; // very quiet bed
  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass';
  lp.frequency.value = 900;
  pad.connect(lp);
  lp.connect(master);

  // A soft minor-ish drone: root, fifth, octave, slightly detuned.
  const freqs = [110, 164.81, 220, 246.94];
  for (const f of freqs) {
    const o = ctx.createOscillator();
    o.type = 'sine';
    o.frequency.value = f;
    o.detune.value = (Math.sin(f) * 8) | 0;
    const g = ctx.createGain();
    g.gain.value = 0.25;
    o.connect(g);
    g.connect(pad);
    o.start();
  }

  // Slow shimmer LFO on the filter for a breathing feel.
  const lfo = ctx.createOscillator();
  lfo.type = 'sine';
  lfo.frequency.value = 0.05;
  const lfoGain = ctx.createGain();
  lfoGain.gain.value = 350;
  lfo.connect(lfoGain);
  lfoGain.connect(lp.frequency);
  lfo.start();
}

/** A short enveloped tone. */
function tone(freq: number, dur: number, type: OscillatorType, when: number, peak = 0.2): void {
  if (!ctx || !master) return;
  const o = ctx.createOscillator();
  o.type = type;
  o.frequency.value = freq;
  const g = ctx.createGain();
  const t0 = ctx.currentTime + when;
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(peak, t0 + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  o.connect(g);
  g.connect(master);
  o.start(t0);
  o.stop(t0 + dur + 0.05);
}

export type Sfx = 'feed' | 'soothe' | 'observe' | 'evolve';

export function sfx(kind: Sfx): void {
  if (!ctx || muted) return;
  switch (kind) {
    case 'feed': // gentle rising two-note
      tone(523.25, 0.25, 'sine', 0, 0.18);
      tone(659.25, 0.3, 'sine', 0.08, 0.16);
      break;
    case 'soothe': // soft low swell
      tone(196, 0.6, 'triangle', 0, 0.14);
      tone(293.66, 0.6, 'sine', 0.02, 0.1);
      break;
    case 'observe': // light bell ping
      tone(880, 0.5, 'sine', 0, 0.14);
      tone(1318.5, 0.4, 'sine', 0.01, 0.06);
      break;
    case 'evolve': // shimmering upward arpeggio
      [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => tone(f, 0.5, 'sine', i * 0.09, 0.16));
      break;
  }
}

export function isMuted(): boolean {
  return muted;
}

/** Toggle mute; returns the new muted state. */
export function toggleMute(): boolean {
  muted = !muted;
  localStorage.setItem(MUTE_KEY, muted ? '1' : '0');
  if (master && ctx) {
    master.gain.setTargetAtTime(muted ? 0 : 1, ctx.currentTime, 0.05);
  }
  return muted;
}
