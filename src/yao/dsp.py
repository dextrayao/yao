"""音訊訊號處理函式 (EQ / 動態 / 降噪 / 空間 / Ducking)。

所有函式都以 float32 單聲道 numpy 陣列 (範圍 [-1, 1]) 運作。
向量化實作,避免 Python 層級的 sample-by-sample 迴圈。
"""

from __future__ import annotations

import numpy as np
from scipy import signal as scisig
from scipy.ndimage import uniform_filter1d


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


def denoise(
    x: np.ndarray,
    sr: int,
    strength: float = 0.8,
    nfft: int = 2048,
    noise_sample: np.ndarray | None = None,
) -> np.ndarray:
    """頻譜降噪 (spectral subtraction with temporal smoothing)。

    從輸入訊號最安靜 10% 的段落估計噪音譜,然後在頻域扣除。
    `strength` 控制扣除強度 (0~1),越大越激進但容易產生 "水底感"。

    若提供 `noise_sample` (一段純噪音音訊),會用它作為噪音樣本,效果更精準。
    """
    if len(x) < nfft * 2:
        return x
    strength = float(np.clip(strength, 0.0, 1.0))
    hop = nfft // 4
    window = "hann"

    _, _, Z = scisig.stft(
        x, fs=sr, window=window, nperseg=nfft, noverlap=nfft - hop
    )
    mag = np.abs(Z)
    phase = np.angle(Z)

    if noise_sample is not None and len(noise_sample) >= nfft:
        _, _, Zn = scisig.stft(
            noise_sample, fs=sr, window=window, nperseg=nfft, noverlap=nfft - hop
        )
        noise_profile = np.mean(np.abs(Zn), axis=1, keepdims=True)
    else:
        frame_energy = mag.sum(axis=0)
        if len(frame_energy) == 0:
            return x
        threshold = np.percentile(frame_energy, 10)
        quiet_mask = frame_energy <= threshold
        if quiet_mask.sum() < 3:
            noise_profile = np.min(mag, axis=1, keepdims=True)
        else:
            noise_profile = np.mean(mag[:, quiet_mask], axis=1, keepdims=True)

    # oversubtraction factor + spectral floor
    alpha = 1.0 + 3.0 * strength           # 1.0 ~ 4.0
    floor = 0.1 - 0.08 * strength          # 0.1 ~ 0.02

    clean_mag = np.maximum(mag - alpha * noise_profile, floor * mag)

    # 時域平滑 gain mask,降低 musical noise artifacts
    gain = clean_mag / np.maximum(mag, 1e-10)
    gain = uniform_filter1d(gain, size=3, axis=1)
    clean_mag = mag * gain

    Z_clean = clean_mag * np.exp(1j * phase)
    _, x_clean = scisig.istft(
        Z_clean, fs=sr, window=window, nperseg=nfft, noverlap=nfft - hop
    )

    out = np.zeros(len(x), dtype=np.float32)
    n = min(len(out), len(x_clean))
    out[:n] = x_clean[:n].astype(np.float32)
    return out


def trim_long_silences(
    x: np.ndarray,
    sr: int,
    threshold_db: float = -40.0,
    max_silence_ms: int = 800,
    keep_silence_ms: int = 300,
    window_ms: int = 20,
) -> np.ndarray:
    """將長於 `max_silence_ms` 的靜音段縮短至 `keep_silence_ms`。

    注意: 會改變音訊長度,**不適合**用在需要與其他軌同步的場合。
    適合單人 podcast 去除冗長停頓。
    """
    if len(x) == 0:
        return x
    window = max(1, int(sr * window_ms / 1000))
    n_windows = len(x) // window
    if n_windows == 0:
        return x

    frames = x[: n_windows * window].reshape(n_windows, window)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    threshold = db_to_gain(threshold_db)
    silent = rms < threshold

    max_silent_samples = int(sr * max_silence_ms / 1000)
    keep_silent_samples = int(sr * keep_silence_ms / 1000)

    keep_mask = np.ones(len(x), dtype=bool)
    i = 0
    while i < n_windows:
        if silent[i]:
            j = i
            while j < n_windows and silent[j]:
                j += 1
            run_samples = (j - i) * window
            if run_samples > max_silent_samples:
                remove = run_samples - keep_silent_samples
                mid_start = i * window + keep_silent_samples // 2
                mid_end = min(mid_start + remove, len(x))
                keep_mask[mid_start:mid_end] = False
            i = j
        else:
            i += 1
    return x[keep_mask].astype(np.float32)


def apply_mutes(
    x: np.ndarray,
    sr: int,
    mute_ranges: list[tuple[float, float]],
    fade_ms: float = 20.0,
) -> np.ndarray:
    """在指定的 [(start_s, end_s), ...] 範圍套用靜音 (含淡入淡出避免 click)。"""
    if not mute_ranges:
        return x
    y = x.copy()
    fade_n = max(1, int(sr * fade_ms / 1000))
    for start_s, end_s in mute_ranges:
        start = max(0, min(int(start_s * sr), len(y)))
        end = max(0, min(int(end_s * sr), len(y)))
        if end <= start:
            continue
        fo_start = max(0, start - fade_n)
        fi_end = min(len(y), end + fade_n)
        if fo_start < start:
            fade_out = np.linspace(1.0, 0.0, start - fo_start, dtype=np.float32)
            y[fo_start:start] = (y[fo_start:start] * fade_out).astype(np.float32)
        y[start:end] = 0
        if end < fi_end:
            fade_in = np.linspace(0.0, 1.0, fi_end - end, dtype=np.float32)
            y[end:fi_end] = (y[end:fi_end] * fade_in).astype(np.float32)
    return y.astype(np.float32)


def detect_transients(
    x: np.ndarray,
    sr: int,
    high_pass_hz: float = 1500.0,
    min_duration_ms: float = 40.0,
    max_duration_ms: float = 600.0,
    ratio_threshold: float = 5.0,
) -> list[tuple[float, float]]:
    """偵測類似咳嗽 / 突發雜音的位置 (候選清單)。

    做法:
      1. 高通濾波 (砍掉基頻,突顯瞬態)
      2. 短時 RMS (10 ms 視窗)
      3. 用 5% 分位數作為廣域 baseline (避免被 burst 本身污染)
      4. 當 rms > ratio_threshold × baseline 視為 burst
      5. 篩選持續時間落在 [min, max] 範圍內的段落

    **這是候選偵測,不是保證準確** — 會把激動的語氣、大笑、爆破音一併抓到。
    使用者需要人工審過產出的時間戳清單,刪掉誤報,再用 `apply_mutes` 套用。
    """
    if len(x) < sr // 10:
        return []

    sos = scisig.butter(4, high_pass_hz, btype="highpass", fs=sr, output="sos")
    y = scisig.sosfilt(sos, x).astype(np.float32)

    window_ms = 10
    window = max(1, int(sr * window_ms / 1000))
    n_frames = len(y) // window
    if n_frames < 10:
        return []
    frames = y[: n_frames * window].reshape(n_frames, window)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)

    # 用全段低分位數當 baseline,對 burst 有抗性
    baseline = max(float(np.percentile(rms, 5)), 1e-5)
    is_burst = rms > ratio_threshold * baseline

    min_frames = max(1, int(min_duration_ms / window_ms))
    max_frames = max(min_frames, int(max_duration_ms / window_ms))

    bursts: list[tuple[float, float]] = []
    i = 0
    pad_s = 0.05  # 前後各多抓 50ms 作為 fade 緩衝
    while i < n_frames:
        if is_burst[i]:
            j = i
            while j < n_frames and is_burst[j]:
                j += 1
            run = j - i
            if min_frames <= run <= max_frames:
                start_s = max(0.0, i * window / sr - pad_s)
                end_s = min(len(x) / sr, j * window / sr + pad_s)
                bursts.append((start_s, end_s))
            i = j
        else:
            i += 1
    return bursts
