"""
長影音剪短影工具 — 從長影片自動擷取社群流量精華片段

功能：
1. 場景偵測：找出影片中的場景切換點
2. 音量能量分析：辨識高能量（說話、音樂高潮）片段
3. 綜合評分：結合場景與音頻分數，挑出最佳精華
4. 匯出短片：輸出適合社群平台的短影片（可設定時長）
"""

import os
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from moviepy import VideoFileClip

logger = logging.getLogger(__name__)


@dataclass
class Segment:
    """代表影片中的一個片段"""
    start: float  # 秒
    end: float    # 秒
    score: float = 0.0
    label: str = ""

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class TrimmerConfig:
    """裁剪設定"""
    min_clip_duration: float = 10.0    # 最短片段（秒）
    max_clip_duration: float = 60.0    # 最長片段（秒）
    target_clip_duration: float = 30.0 # 目標片段長度（秒）
    max_clips: int = 5                 # 最多輸出幾段
    audio_sample_window: float = 1.0   # 音頻分析窗口（秒）
    scene_threshold: float = 30.0      # 場景偵測閾值（像素差異）
    padding: float = 0.5              # 片段前後留白（秒）
    output_format: str = "mp4"
    output_dir: str = "output_clips"
    # 社群平台預設
    platform: str = "general"  # general, tiktok, instagram, youtube_shorts


# 各平台建議時長
PLATFORM_PRESETS = {
    "general": {"min": 10, "max": 60, "target": 30},
    "tiktok": {"min": 15, "max": 60, "target": 30},
    "instagram": {"min": 10, "max": 90, "target": 30},
    "youtube_shorts": {"min": 15, "max": 60, "target": 45},
}


class VideoAnalyzer:
    """分析影片，找出精華片段"""

    def __init__(self, video_path: str, config: TrimmerConfig | None = None):
        self.video_path = video_path
        self.config = config or TrimmerConfig()
        self._apply_platform_preset()
        self.clip: VideoFileClip | None = None

    def _apply_platform_preset(self):
        preset = PLATFORM_PRESETS.get(self.config.platform)
        if preset and self.config.platform != "general":
            self.config.min_clip_duration = preset["min"]
            self.config.max_clip_duration = preset["max"]
            self.config.target_clip_duration = preset["target"]

    def load(self) -> "VideoAnalyzer":
        """載入影片"""
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"找不到影片：{self.video_path}")
        self.clip = VideoFileClip(self.video_path)
        logger.info(
            f"已載入影片：{self.video_path} "
            f"(時長 {self.clip.duration:.1f}s, "
            f"{self.clip.w}x{self.clip.h}, "
            f"{self.clip.fps:.1f} fps)"
        )
        return self

    def close(self):
        if self.clip:
            self.clip.close()
            self.clip = None

    def __enter__(self):
        return self.load()

    def __exit__(self, *args):
        self.close()

    def analyze_audio_energy(self) -> list[tuple[float, float]]:
        """
        分析音頻能量，回傳每個時間窗口的 (時間點, 能量值)。
        高能量 = 說話聲大、音樂高潮、觀眾反應等。
        """
        if not self.clip or not self.clip.audio:
            logger.warning("影片沒有音軌，跳過音頻分析")
            return []

        audio = self.clip.audio
        sample_rate = 22050
        window = self.config.audio_sample_window

        # 取得完整音頻數據
        audio_frames = audio.to_soundarray(fps=sample_rate)
        if audio_frames.ndim > 1:
            audio_mono = np.mean(audio_frames, axis=1)
        else:
            audio_mono = audio_frames

        # 計算每個窗口的 RMS 能量
        samples_per_window = int(sample_rate * window)
        energy_timeline = []

        for i in range(0, len(audio_mono) - samples_per_window, samples_per_window):
            chunk = audio_mono[i : i + samples_per_window]
            rms = np.sqrt(np.mean(chunk ** 2))
            time_point = i / sample_rate
            energy_timeline.append((time_point, float(rms)))

        logger.info(f"音頻分析完成：{len(energy_timeline)} 個窗口")
        return energy_timeline

    def detect_scenes(self) -> list[float]:
        """
        偵測場景切換點。
        使用相鄰幀的像素差異來判斷場景變化。
        """
        if not self.clip:
            return []

        scene_changes = []
        fps = self.clip.fps
        # 每 0.5 秒取一幀來比較，降低計算量
        sample_interval = max(0.5, 1.0 / fps)
        prev_frame = None
        threshold = self.config.scene_threshold

        total_frames = int(self.clip.duration / sample_interval)
        logger.info(f"開始場景偵測（共 {total_frames} 個取樣點）...")

        t = 0.0
        while t < self.clip.duration:
            try:
                frame = self.clip.get_frame(t)
                # 縮小幀尺寸加速計算
                small = frame[::4, ::4].astype(np.float32)

                if prev_frame is not None:
                    diff = np.mean(np.abs(small - prev_frame))
                    if diff > threshold:
                        scene_changes.append(t)
                        logger.debug(f"  場景切換 @ {t:.1f}s (差異 {diff:.1f})")

                prev_frame = small
            except Exception:
                pass
            t += sample_interval

        logger.info(f"場景偵測完成：找到 {len(scene_changes)} 個切換點")
        return scene_changes

    def find_highlights(self) -> list[Segment]:
        """
        綜合場景偵測與音頻能量分析，找出最佳精華片段。
        """
        if not self.clip:
            raise RuntimeError("請先呼叫 load() 載入影片")

        energy_timeline = self.analyze_audio_energy()
        scene_changes = self.detect_scenes()

        # 建立候選片段（以場景切換點為分割基準）
        boundaries = [0.0] + scene_changes + [self.clip.duration]
        boundaries = sorted(set(boundaries))

        candidates: list[Segment] = []
        target = self.config.target_clip_duration
        min_dur = self.config.min_clip_duration
        max_dur = self.config.max_clip_duration

        # 策略：用滑動窗口在影片上產生候選片段
        step = max(min_dur / 2, 5.0)
        t = 0.0
        while t + min_dur <= self.clip.duration:
            end = min(t + target, self.clip.duration)
            duration = end - t
            if duration < min_dur:
                t += step
                continue
            if duration > max_dur:
                end = t + max_dur

            # 計算這個區間的音頻能量分數
            segment_energy = [
                e for (tp, e) in energy_timeline if t <= tp < end
            ]
            avg_energy = np.mean(segment_energy) if segment_energy else 0.0

            # 計算場景豐富度分數（場景變化多 = 視覺上更有趣）
            scene_count = sum(1 for sc in scene_changes if t < sc < end)
            scene_score = min(scene_count / 3.0, 1.0)  # 正規化到 0~1

            # 綜合分數：70% 音頻能量 + 30% 場景豐富度
            combined = 0.7 * (avg_energy / max(
                (e for _, e in energy_timeline), default=1.0
            )) + 0.3 * scene_score

            candidates.append(Segment(
                start=t,
                end=end,
                score=combined,
                label=f"energy={avg_energy:.3f}, scenes={scene_count}",
            ))
            t += step

        # 排序並挑選不重疊的最佳片段
        candidates.sort(key=lambda s: s.score, reverse=True)
        selected = self._select_non_overlapping(candidates)

        # 按時間順序排列
        selected.sort(key=lambda s: s.start)
        logger.info(f"已選出 {len(selected)} 個精華片段")
        for i, seg in enumerate(selected):
            logger.info(
                f"  片段 {i+1}: {seg.start:.1f}s ~ {seg.end:.1f}s "
                f"({seg.duration:.1f}s) score={seg.score:.3f} [{seg.label}]"
            )
        return selected

    def _select_non_overlapping(self, candidates: list[Segment]) -> list[Segment]:
        """從候選片段中選出不重疊的 top N"""
        selected: list[Segment] = []
        for seg in candidates:
            if len(selected) >= self.config.max_clips:
                break
            overlaps = any(
                not (seg.end <= s.start or seg.start >= s.end)
                for s in selected
            )
            if not overlaps:
                selected.append(seg)
        return selected


class VideoTrimmer:
    """根據分析結果裁剪影片並匯出"""

    def __init__(self, video_path: str, config: TrimmerConfig | None = None):
        self.video_path = video_path
        self.config = config or TrimmerConfig()

    def trim_and_export(self, segments: list[Segment]) -> list[str]:
        """
        將指定片段從原始影片裁剪出來並儲存。
        回傳輸出檔案路徑列表。
        """
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        source_name = Path(self.video_path).stem
        output_paths: list[str] = []

        with VideoFileClip(self.video_path) as clip:
            for i, seg in enumerate(segments, 1):
                start = max(0, seg.start - self.config.padding)
                end = min(clip.duration, seg.end + self.config.padding)

                sub = clip.subclipped(start, end)

                filename = f"{source_name}_clip{i:02d}_{start:.0f}s-{end:.0f}s.{self.config.output_format}"
                output_path = str(output_dir / filename)

                logger.info(f"匯出片段 {i}/{len(segments)}: {output_path}")
                sub.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    logger=None,  # 減少 moviepy 內部 log
                )
                output_paths.append(output_path)

        return output_paths


def process_video(
    video_path: str,
    config: TrimmerConfig | None = None,
    save_report: bool = True,
) -> list[str]:
    """
    完整流程：分析 + 裁剪 + 匯出。
    回傳輸出檔案路徑列表。
    """
    config = config or TrimmerConfig()

    with VideoAnalyzer(video_path, config) as analyzer:
        segments = analyzer.find_highlights()

    if not segments:
        logger.warning("未找到精華片段")
        return []

    trimmer = VideoTrimmer(video_path, config)
    output_paths = trimmer.trim_and_export(segments)

    if save_report:
        report = {
            "source": video_path,
            "platform": config.platform,
            "clips": [
                {
                    "file": path,
                    "start": seg.start,
                    "end": seg.end,
                    "duration": seg.duration,
                    "score": seg.score,
                    "detail": seg.label,
                }
                for seg, path in zip(segments, output_paths)
            ],
        }
        report_path = Path(config.output_dir) / f"{Path(video_path).stem}_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"分析報告已儲存：{report_path}")

    return output_paths
