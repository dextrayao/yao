#!/usr/bin/env python3
"""
長影音剪短影 CLI — 從 MP4 長影片自動擷取社群精華片段

用法：
    python main.py input.mp4
    python main.py input.mp4 --platform tiktok --max-clips 3
    python main.py input.mp4 --min-duration 15 --max-duration 45 --output-dir my_clips
"""

import argparse
import logging
import sys

from video_trimmer import TrimmerConfig, process_video, PLATFORM_PRESETS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="從長影片自動擷取社群流量精華片段",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python main.py my_video.mp4
  python main.py my_video.mp4 --platform tiktok --max-clips 3
  python main.py my_video.mp4 --target-duration 45 --output-dir shorts/
        """,
    )
    parser.add_argument("video", help="輸入影片路徑（MP4）")
    parser.add_argument(
        "--platform",
        choices=list(PLATFORM_PRESETS.keys()),
        default="general",
        help="目標社群平台（預設：general）",
    )
    parser.add_argument("--max-clips", type=int, default=5, help="最多輸出幾段（預設：5）")
    parser.add_argument("--min-duration", type=float, help="最短片段秒數")
    parser.add_argument("--max-duration", type=float, help="最長片段秒數")
    parser.add_argument("--target-duration", type=float, help="目標片段秒數")
    parser.add_argument("--scene-threshold", type=float, default=30.0, help="場景偵測閾值（預設：30）")
    parser.add_argument("--output-dir", default="output_clips", help="輸出目錄（預設：output_clips）")
    parser.add_argument("--no-report", action="store_true", help="不儲存分析報告 JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="顯示詳細 log")
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    config = TrimmerConfig(
        max_clips=args.max_clips,
        scene_threshold=args.scene_threshold,
        output_dir=args.output_dir,
        platform=args.platform,
    )

    if args.min_duration is not None:
        config.min_clip_duration = args.min_duration
    if args.max_duration is not None:
        config.max_clip_duration = args.max_duration
    if args.target_duration is not None:
        config.target_clip_duration = args.target_duration

    print(f"影片：{args.video}")
    print(f"平台：{config.platform}")
    print(f"片段長度：{config.min_clip_duration:.0f}~{config.max_clip_duration:.0f}s（目標 {config.target_clip_duration:.0f}s）")
    print(f"最多輸出：{config.max_clips} 段")
    print(f"輸出目錄：{config.output_dir}")
    print("-" * 50)

    try:
        output_paths = process_video(
            args.video,
            config=config,
            save_report=not args.no_report,
        )
    except FileNotFoundError as e:
        print(f"錯誤：{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logging.exception("處理過程中發生錯誤")
        print(f"錯誤：{e}", file=sys.stderr)
        sys.exit(1)

    if output_paths:
        print("-" * 50)
        print(f"完成！已匯出 {len(output_paths)} 個精華片段：")
        for p in output_paths:
            print(f"  {p}")
    else:
        print("未找到適合的精華片段。可嘗試調低 --scene-threshold 或調整片段長度設定。")


if __name__ == "__main__":
    main()
