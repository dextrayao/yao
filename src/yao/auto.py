"""單一指令自動處理: 原始錄音 → 乾淨母帶 MP3 (+ 可選 metadata)。

與 `mixer.mix_podcast()` 的差別:
- 只接收一個人聲檔案 (不做多軌 / 背景音樂 / 片頭片尾)
- 預設開啟降噪 + 長停頓裁剪
- 所有參數都有合理預設值,目的是最小化使用者配置工作

設計理念: Logic Pro 的替代品,但輸入只有原始錄音、輸出直接能發佈。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from . import dsp, mixer


def parse_mutes_file(path: Path) -> list[tuple[float, float]]:
    """解析靜音範圍檔案。

    每行兩個時間 (空白分隔),支援下列格式:
        12.5 14.3              (純秒數)
        00:12 00:14            (MM:SS)
        00:12.5 00:14.3        (MM:SS.ms)
        01:02:03 01:02:05      (HH:MM:SS)

    `#` 開頭的行視為註解,空行忽略。
    """

    def to_seconds(s: str) -> float:
        s = s.strip()
        if ":" not in s:
            return float(s)
        parts = s.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        raise ValueError(f"時間格式無法解析: {s}")

    ranges: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            start = to_seconds(parts[0])
            end = to_seconds(parts[1])
        except ValueError:
            continue
        if end > start:
            ranges.append((start, end))
    return ranges


def write_mutes_file(path: Path, candidates: list[tuple[float, float]]) -> None:
    """把偵測到的候選時間戳寫成文字檔,供使用者審閱。"""
    lines = [
        "# yao detect 產出的候選靜音範圍",
        "# 每行格式: <起始> <結束>   (秒數 或 MM:SS.ms)",
        "# 審閱後保留要抹掉的段落,其他用 # 註解掉,",
        "# 然後用 `yao auto <input.wav> --mutes <此檔>` 重新處理。",
        "",
    ]
    for start, end in candidates:
        start_mm = int(start // 60)
        start_ss = start - start_mm * 60
        end_mm = int(end // 60)
        end_ss = end - end_mm * 60
        lines.append(f"{start_mm:02d}:{start_ss:05.2f}  {end_mm:02d}:{end_ss:05.2f}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def auto_process(
    input_path: Path,
    output_dir: Path,
    *,
    denoise: bool = True,
    denoise_strength: float = 0.8,
    trim_silence: bool = True,
    max_silence_ms: int = 800,
    keep_silence_ms: int = 300,
    mutes: list[tuple[float, float]] | None = None,
    high_pass_hz: float = 80.0,
    compressor: dict[str, float] | None = None,
    presence_db: float = 2.5,
    target_lufs: float = -16.0,
    limiter_ceiling_db: float = -1.0,
    bitrate: str = "192k",
    log: Any = print,
) -> Path:
    """對單一人聲檔案執行全自動母帶處理,回傳輸出 MP3 路徑。"""
    sr = mixer.SAMPLE_RATE
    output_dir.mkdir(parents=True, exist_ok=True)

    log(f"[auto] 載入: {input_path}")
    x = mixer.load_audio(input_path, sr)
    orig_len = len(x) / sr
    log(f"[auto] 原始長度: {orig_len:.1f}s")

    if mutes:
        log(f"[auto] 套用 {len(mutes)} 段手動靜音範圍")
        x = dsp.apply_mutes(x, sr, mutes)

    if denoise:
        log(f"[auto] 頻譜降噪 (strength={denoise_strength})")
        x = dsp.denoise(x, sr, strength=denoise_strength)

    if trim_silence:
        log(f"[auto] 裁剪 >{max_silence_ms}ms 的靜音段 (保留 {keep_silence_ms}ms)")
        before = len(x)
        x = dsp.trim_long_silences(
            x, sr,
            max_silence_ms=max_silence_ms,
            keep_silence_ms=keep_silence_ms,
        )
        saved = (before - len(x)) / sr
        log(f"[auto] 裁剪後長度: {len(x)/sr:.1f}s (省下 {saved:.1f}s)")

    log(f"[auto] 高通 {high_pass_hz} Hz")
    x = dsp.high_pass(x, high_pass_hz, sr)

    comp = compressor or {"threshold_db": -20.0, "ratio": 3.0, "time_ms": 20.0}
    log(
        f"[auto] 壓縮 ratio={comp['ratio']}:1 "
        f"threshold={comp['threshold_db']}dB"
    )
    x = dsp.compress(x, sr=sr, **comp)

    if presence_db:
        log(f"[auto] 清晰度 +{presence_db}dB @ 4kHz")
        x = dsp.presence_boost(x, sr, gain_db=presence_db)

    log(f"[auto] 響度正規化 → {target_lufs} LUFS")
    x = dsp.normalize_loudness(x, target_lufs, sr)

    log(f"[auto] 峰值限制 ceiling={limiter_ceiling_db}dB")
    x = dsp.peak_limit(x, ceiling_db=limiter_ceiling_db)

    out_mp3 = output_dir / f"{input_path.stem}_mastered.mp3"
    mixer.save_mp3(x, out_mp3, sr=sr, bitrate=bitrate)
    final_len = len(x) / sr
    log(f"[auto] ✓ 輸出 MP3: {out_mp3} ({final_len:.1f}s)")
    return out_mp3


def detect_cough_candidates(
    input_path: Path,
    output_path: Path,
    *,
    high_pass_hz: float = 1500.0,
    ratio_threshold: float = 5.0,
    log: Any = print,
) -> list[tuple[float, float]]:
    """偵測候選靜音段並寫成文字檔。"""
    sr = mixer.SAMPLE_RATE
    log(f"[detect] 載入: {input_path}")
    x = mixer.load_audio(input_path, sr)
    log(f"[detect] 分析 {len(x)/sr:.1f}s 音訊...")
    bursts = dsp.detect_transients(
        x, sr,
        high_pass_hz=high_pass_hz,
        ratio_threshold=ratio_threshold,
    )
    log(f"[detect] 找到 {len(bursts)} 個候選 burst")
    for start, end in bursts:
        log(f"        {start:7.2f}s ~ {end:7.2f}s   ({(end - start) * 1000:.0f}ms)")
    write_mutes_file(output_path, bursts)
    log(f"[detect] ✓ 已寫入: {output_path}")
    log("[detect] 用文字編輯器審閱,保留要抹掉的行、其他加 # 註解,再用:")
    log(f"         yao auto {input_path.name} --mutes {output_path.name}")
    return bursts
