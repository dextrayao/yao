"""音訊訊號處理函式 (EQ / 動態 / 降噪 / 空間 / Ducking)。

所有函式都以 float32 單聲道 numpy 陣列 (範圍 [-1, 1]) 運作。
向量化實作,避免 Python 層級的 sample-by-sample 迴圈。
"""

from __future__ import annotations

import numpy as np
from scipy import signal as scisig


def db_to_gain(db: float) -> float:
    return float(10 ** (db / 20))


def gain_to_db(gain: float) -> float:
    return float(20 * np.log10(max(gain, 1e-12)))


def high_pass(x: np.ndarray, cutoff_hz: float, sr: int, order: int = 4) -> np.ndarray:
    """Butterworth 高通濾波器 — 移除低頻雜訊 (空調聲、噴麥)。"""
    sos = scisig.butter(order, cutoff_hz, btype="highpass", fs=sr, output="sos")
    return scisig.sosfilt(sos, x).astype(np.float32)


def low_pass(x: np.ndarray, cutoff_hz: float, sr: int, order: int = 4) -> np.ndarray:
    sos = scisig.butter(order, cutoff_hz, btype="lowpass", fs=sr, output="sos")
    return scisig.sosfilt(sos, x).astype(np.float32)


def presence_boost(x: np.ndarray, sr: int, gain_db: float = 3.0) -> np.ndarray:
    """在 3~5 kHz 做溫和 peaking,增強人聲清晰度。"""
    freq = 4000.0
    q = 0.7
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * q)
    A = 10 ** (gain_db / 40)
    cos_w0 = np.cos(w0)
    b0 = 1 + alpha * A
    b1 = -2 * cos_w0
    b2 = 1 - alpha * A
    a0 = 1 + alpha / A
    a1 = -2 * cos_w0
    a2 = 1 - alpha / A
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    return scisig.lfilter(b, a, x).astype(np.float32)


def compress(
    x: np.ndarray,
    threshold_db: float,
    ratio: float,
    time_ms: float = 20.0,
    sr: int = 44100,
) -> np.ndarray:
    """前饋式單波段壓縮器。

    使用一階低通濾波 (one-pole) 作為對稱 attack/release 包絡線追蹤器。
    這不是真正的非對稱設計,但對人聲 podcast 已夠穩定且快得多。
    """
    if ratio <= 1.0:
        return x.astype(np.float32)

    alpha = float(np.exp(-1.0 / (sr * time_ms / 1000.0)))
    abs_x = np.abs(x).astype(np.float32)
    # y[n] = (1-alpha) * x[n] + alpha * y[n-1]  → IIR [1-alpha] / [1, -alpha]
    env = scisig.lfilter([1.0 - alpha], [1.0, -alpha], abs_x).astype(np.float32)
    env = np.maximum(env, 1e-8)

    threshold = db_to_gain(threshold_db)
    gain = np.ones_like(env)
    over = env > threshold
    gain[over] = (threshold + (env[over] - threshold) / ratio) / env[over]

    # Makeup gain: 補償壓縮後整體音量下降
    makeup_db = (1.0 - 1.0 / ratio) * (-threshold_db) * 0.5
    makeup = db_to_gain(makeup_db)
    return (x * gain * makeup).astype(np.float32)


def duck_music(
    music: np.ndarray,
    voice: np.ndarray,
    attenuation_db: float = -12.0,
    threshold_db: float = -40.0,
    smooth_hz: float = 3.0,
    sr: int = 44100,
) -> np.ndarray:
    """當人聲出現時自動調低背景音樂 (side-chain ducking)。

    做法: 對人聲取絕對值 → 低通平滑 → 超過門檻時套用衰減 → 再對 gain
    curve 低通濾波,避免切換瞬間產生 click。
    """
    n = min(len(music), len(voice))
    music = music[:n].astype(np.float32)
    voice = voice[:n]

    # 人聲包絡線 (10 Hz 低通)
    abs_v = np.abs(voice).astype(np.float32)
    b_env, a_env = scisig.butter(2, 10.0 / (sr / 2), btype="lowpass")
    env = scisig.lfilter(b_env, a_env, abs_v).astype(np.float32)

    threshold = db_to_gain(threshold_db)
    duck = db_to_gain(attenuation_db)
    gain = np.where(env > threshold, duck, 1.0).astype(np.float32)

    # 平滑 gain curve,避免瞬間跳變
    b_g, a_g = scisig.butter(2, smooth_hz / (sr / 2), btype="lowpass")
    smooth_gain = scisig.lfilter(b_g, a_g, gain).astype(np.float32)
    smooth_gain = np.clip(smooth_gain, duck, 1.0)

    return (music * smooth_gain).astype(np.float32)


def _k_weight(x: np.ndarray, sr: int) -> np.ndarray:
    """近似 ITU-R BS.1770 K-weighting: 高通 + 高頻 shelf。"""
    # 高通 38 Hz
    b1, a1 = scisig.butter(2, 38.0 / (sr / 2), btype="highpass")
    y = scisig.lfilter(b1, a1, x)
    # 高頻 shelf 約 +4 dB @ 1.5 kHz (粗略近似)
    freq = 1500.0
    gain_db = 4.0
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / 2 * np.sqrt((A + 1 / A) * (1 / 0.707 - 1) + 2)
    cos_w0 = np.cos(w0)
    b0 = A * ((A + 1) + (A - 1) * cos_w0 + 2 * np.sqrt(A) * alpha)
    b1s = -2 * A * ((A - 1) + (A + 1) * cos_w0)
    b2 = A * ((A + 1) + (A - 1) * cos_w0 - 2 * np.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * cos_w0 + 2 * np.sqrt(A) * alpha
    a1s = 2 * ((A - 1) - (A + 1) * cos_w0)
    a2 = (A + 1) - (A - 1) * cos_w0 - 2 * np.sqrt(A) * alpha
    b = np.array([b0, b1s, b2]) / a0
    a = np.array([1.0, a1s / a0, a2 / a0])
    return scisig.lfilter(b, a, y).astype(np.float32)


def normalize_loudness(x: np.ndarray, target_lufs: float, sr: int) -> np.ndarray:
    """近似 integrated LUFS 正規化。

    注意: 這是輕量近似,不是完整的 BS.1770-4 實作 (沒有 gating)。
    對 podcast 的使用場景通常足夠;若需精確量測請用 pyloudnorm。
    """
    if len(x) == 0:
        return x
    weighted = _k_weight(x, sr)
    mean_square = float(np.mean(weighted ** 2))
    if mean_square < 1e-12:
        return x
    # LUFS ≈ -0.691 + 10*log10(mean_square)
    current_lufs = -0.691 + 10 * np.log10(mean_square)
    gain_db = target_lufs - current_lufs
    gain = db_to_gain(gain_db)
    return (x * gain).astype(np.float32)


def peak_limit(x: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    """確保峰值不超過 ceiling_db (等比例縮放,無失真)。"""
    ceiling = db_to_gain(ceiling_db)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak > ceiling and peak > 0:
        x = x * (ceiling / peak)
    return x.astype(np.float32)


def noise_gate(
    x: np.ndarray,
    threshold_db: float = -50.0,
    attack_ms: float = 5.0,
    release_ms: float = 100.0,
    sr: int = 44100,
) -> np.ndarray:
    """簡易 noise gate — 低於門檻時靜音,平滑淡出淡入。"""
    alpha_a = float(np.exp(-1.0 / (sr * attack_ms / 1000.0)))
    alpha_r = float(np.exp(-1.0 / (sr * release_ms / 1000.0)))
    abs_x = np.abs(x).astype(np.float32)
    env = scisig.lfilter([1.0 - alpha_r], [1.0, -alpha_r], abs_x).astype(np.float32)
    threshold = db_to_gain(threshold_db)
    raw_gate = (env > threshold).astype(np.float32)
    b, a = scisig.butter(2, 20.0 / (sr / 2), btype="lowpass")
    _ = alpha_a  # 保留 API,目前以對稱平滑實作
    smooth_gate = scisig.lfilter(b, a, raw_gate).astype(np.float32)
    smooth_gate = np.clip(smooth_gate, 0.0, 1.0)
    return (x * smooth_gate).astype(np.float32)
