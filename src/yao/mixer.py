"""混音管線 — 將多個音軌整合為最終 podcast 母帶。

流程:
    load → voice 處理 (high-pass, gate, compress, presence, normalize)
         → music 處理 (gain, loop, ducking)
         → mix (voice + music)
         → concat (intro + body + outro)
         → loudness normalize → peak limit → export MP3
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from pydub import AudioSegment

from . import dsp

SAMPLE_RATE = 44100


def load_audio(path: str | Path, sr: int = SAMPLE_RATE) -> np.ndarray:
    """載入任意格式音訊 → float32 mono,範圍 [-1, 1]。"""
    seg = AudioSegment.from_file(str(path))
    seg = seg.set_frame_rate(sr).set_channels(1).set_sample_width(2)
    samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


def save_mp3(
    samples: np.ndarray,
    path: str | Path,
    sr: int = SAMPLE_RATE,
    bitrate: str = "192k",
) -> None:
    """將 float32 mono 陣列輸出為 MP3 (需要 ffmpeg)。"""
    samples = np.clip(samples, -1.0, 1.0)
    int_samples = (samples * 32767).astype(np.int16)
    seg = AudioSegment(
        int_samples.tobytes(),
        frame_rate=sr,
        sample_width=2,
        channels=1,
    )
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    seg.export(str(out), format="mp3", bitrate=bitrate)


def _apply_gain(x: np.ndarray, gain_db: float) -> np.ndarray:
    if gain_db == 0:
        return x
    return (x * dsp.db_to_gain(gain_db)).astype(np.float32)


def _peak_normalize(x: np.ndarray, target_db: float) -> np.ndarray:
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak <= 0:
        return x
    target = dsp.db_to_gain(target_db)
    return (x * (target / peak)).astype(np.float32)


def _loop_to_length(x: np.ndarray, length: int) -> np.ndarray:
    if len(x) == 0:
        return np.zeros(length, dtype=np.float32)
    if len(x) >= length:
        return x[:length].astype(np.float32)
    reps = int(np.ceil(length / len(x)))
    return np.tile(x, reps)[:length].astype(np.float32)


def process_voice(voice: np.ndarray, cfg: dict[str, Any], sr: int) -> np.ndarray:
    """套用人聲處理鏈: 高通 → 噪音門 → 壓縮 → 清晰度 → peak normalize。"""
    x = voice.astype(np.float32)

    hp = cfg.get("high_pass_hz")
    if hp:
        x = dsp.high_pass(x, float(hp), sr)

    gate = cfg.get("noise_gate")
    if gate:
        x = dsp.noise_gate(
            x,
            threshold_db=float(gate.get("threshold_db", -50)),
            sr=sr,
        )

    comp = cfg.get("compressor")
    if comp:
        x = dsp.compress(
            x,
            threshold_db=float(comp.get("threshold_db", -20)),
            ratio=float(comp.get("ratio", 3.0)),
            time_ms=float(comp.get("time_ms", 20)),
            sr=sr,
        )

    presence = cfg.get("presence_boost_db")
    if presence:
        x = dsp.presence_boost(x, sr, gain_db=float(presence))

    peak_db = cfg.get("normalize_peak_db")
    if peak_db is not None:
        x = _peak_normalize(x, float(peak_db))

    return x


def build_voice_bus(voice_cfgs: list[dict[str, Any]], sr: int) -> np.ndarray:
    """載入並混合多個人聲音軌 (例如主持人 + 來賓)。"""
    if not voice_cfgs:
        raise ValueError("至少需要一個 voice 音軌")

    loaded = []
    max_len = 0
    for v in voice_cfgs:
        arr = load_audio(v["path"], sr)
        arr = _apply_gain(arr, float(v.get("gain_db", 0)))
        loaded.append(arr)
        max_len = max(max_len, len(arr))

    bus = np.zeros(max_len, dtype=np.float32)
    for arr in loaded:
        bus[: len(arr)] += arr
    return bus


def build_music_bus(
    music_cfg: dict[str, Any],
    voice: np.ndarray,
    ducking_cfg: dict[str, Any],
    sr: int,
) -> np.ndarray:
    """載入背景音樂,延展至人聲長度,套用 ducking。"""
    music = load_audio(music_cfg["path"], sr)
    music = _apply_gain(music, float(music_cfg.get("gain_db", -18)))
    music = _loop_to_length(music, len(voice))

    if ducking_cfg.get("enabled", True):
        music = dsp.duck_music(
            music,
            voice,
            attenuation_db=float(ducking_cfg.get("attenuation_db", -12)),
            threshold_db=float(ducking_cfg.get("threshold_db", -40)),
            smooth_hz=float(ducking_cfg.get("smooth_hz", 3.0)),
            sr=sr,
        )
    return music


def mix_tracks(cfg: dict[str, Any]) -> np.ndarray:
    """執行整個混音管線並回傳最終 float32 樣本陣列。"""
    sr = SAMPLE_RATE
    tracks = cfg.get("tracks", {})
    processing = cfg.get("processing", {})

    # 1. Voice
    voice = build_voice_bus(tracks.get("voice", []), sr)
    voice = process_voice(voice, processing.get("voice", {}), sr)

    # 2. Music + Ducking
    music_cfg = tracks.get("music")
    if music_cfg:
        music = build_music_bus(
            music_cfg, voice, processing.get("ducking", {}), sr
        )
    else:
        music = np.zeros(len(voice), dtype=np.float32)

    body = voice + music

    # 3. Intro / Outro
    parts: list[np.ndarray] = []

    intro_cfg = tracks.get("intro")
    if intro_cfg:
        intro = load_audio(intro_cfg["path"], sr)
        intro = _apply_gain(intro, float(intro_cfg.get("gain_db", 0)))
        parts.append(intro)

    parts.append(body)

    outro_cfg = tracks.get("outro")
    if outro_cfg:
        outro = load_audio(outro_cfg["path"], sr)
        outro = _apply_gain(outro, float(outro_cfg.get("gain_db", 0)))
        parts.append(outro)

    final = np.concatenate(parts) if len(parts) > 1 else parts[0]

    # 4. Master: 響度正規化 + 峰值限制
    out_cfg = processing.get("output", {})
    target_lufs = float(out_cfg.get("target_lufs", -16.0))
    final = dsp.normalize_loudness(final, target_lufs, sr)
    final = dsp.peak_limit(final, ceiling_db=float(out_cfg.get("limiter_ceiling_db", -1.0)))

    return final


def mix_podcast(cfg: dict[str, Any]) -> Path:
    """混音並輸出 MP3,回傳輸出路徑。"""
    samples = mix_tracks(cfg)
    out_cfg = cfg.get("output", {})
    out_path = Path(out_cfg.get("path", "output/episode.mp3"))
    save_mp3(
        samples,
        out_path,
        sr=SAMPLE_RATE,
        bitrate=str(out_cfg.get("bitrate", "192k")),
    )
    return out_path
