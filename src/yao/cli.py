"""Yao CLI — podcast 混音、自動母帶、metadata 產生。

子指令:
  yao auto <input.wav>      # 單檔案自動處理 (降噪 + 母帶 + 可選 metadata)
  yao detect <input.wav>    # 偵測候選咳嗽/雜音位置,產出 mutes.txt 樣板
  yao mix <config.yaml>     # 使用 YAML 設定檔執行完整多軌混音
  yao <config.yaml>         # 與 `yao mix` 相同 (向後相容捷徑)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .auto import auto_process, detect_cough_candidates, parse_mutes_file
from .metadata import generate_metadata
from .mixer import mix_podcast


# ---------------------------------------------------------------------------
# mix (config-driven) 模式
# ---------------------------------------------------------------------------


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"錯誤: 設定檔不存在: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if not isinstance(cfg, dict):
        print("錯誤: 設定檔必須是 YAML mapping", file=sys.stderr)
        sys.exit(1)
    return cfg


def _run_mix(cfg: dict[str, Any]) -> None:
    print("[1/2] 開始混音...")
    out_path = mix_podcast(cfg)
    print(f"       已輸出 MP3: {out_path}")


def _run_metadata_from_cfg(cfg: dict[str, Any]) -> None:
    meta_cfg = cfg.get("metadata", {}) or {}
    transcript_path = cfg.get("transcript")
    if not transcript_path:
        print("[2/2] 跳過 metadata (設定檔未指定 transcript)")
        return

    tpath = Path(transcript_path)
    if not tpath.exists():
        print(f"[2/2] 警告: 逐字稿不存在,跳過 metadata: {tpath}", file=sys.stderr)
        return

    print("[2/2] 呼叫 Claude 產生 metadata...")
    _generate_and_save_metadata(
        transcript=tpath.read_text(encoding="utf-8"),
        hints=str(meta_cfg.get("topic_hints", "")),
        language=str(meta_cfg.get("language", "zh-TW")),
        model=str(meta_cfg.get("model", "claude-opus-4-6")),
        output_path=Path(meta_cfg.get("output_path", "output/metadata.json")),
    )


def _cmd_mix(args: argparse.Namespace) -> int:
    cfg = _load_config(args.config)
    if not args.skip_mix:
        _run_mix(cfg)
    else:
        print("[1/2] 已跳過混音")
    if not args.skip_metadata:
        _run_metadata_from_cfg(cfg)
    else:
        print("[2/2] 已跳過 metadata 產生")
    return 0


# ---------------------------------------------------------------------------
# auto (single-file) 模式
# ---------------------------------------------------------------------------


def _generate_and_save_metadata(
    transcript: str,
    hints: str,
    language: str,
    model: str,
    output_path: Path,
) -> None:
    result = generate_metadata(
        transcript=transcript,
        hints=hints,
        language=language,
        model=model,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    usage = result.get("_usage", {})
    print(f"       已輸出 metadata: {output_path}")
    print(f"       標題: {result.get('title', '')}")
    print(f"       摘要: {result.get('summary', '')}")
    tags = result.get("hashtags") or []
    if tags:
        print(f"       hashtag: {' '.join('#' + t for t in tags)}")
    if usage:
        print(
            "       usage: input={input_tokens} output={output_tokens} "
            "cache_read={cache_read_input_tokens}".format(**usage)
        )


def _cmd_auto(args: argparse.Namespace) -> int:
    input_path: Path = args.input
    if not input_path.exists():
        print(f"錯誤: 音訊檔不存在: {input_path}", file=sys.stderr)
        return 1

    mutes = None
    if args.mutes:
        if not args.mutes.exists():
            print(f"錯誤: mutes 檔案不存在: {args.mutes}", file=sys.stderr)
            return 1
        mutes = parse_mutes_file(args.mutes)
        print(f"[auto] 從 {args.mutes} 讀到 {len(mutes)} 段靜音範圍")

    out_mp3 = auto_process(
        input_path=input_path,
        output_dir=args.out,
        denoise=not args.no_denoise,
        denoise_strength=args.denoise_strength,
        trim_silence=not args.no_trim,
        max_silence_ms=args.max_silence_ms,
        mutes=mutes,
        target_lufs=args.target_lufs,
    )

    if args.no_metadata:
        print("[meta] 已跳過 metadata 產生")
        return 0

    transcript_path: Path | None = args.transcript
    if transcript_path is None:
        print("[meta] 未提供 --transcript,跳過 metadata (想要標題/說明/hashtag 請加此參數)")
        return 0

    if not transcript_path.exists():
        print(f"[meta] 警告: 逐字稿不存在,跳過 metadata: {transcript_path}", file=sys.stderr)
        return 0

    print("[meta] 呼叫 Claude 產生標題 / 說明 / hashtag...")
    metadata_out = args.out / f"{input_path.stem}_metadata.json"
    _generate_and_save_metadata(
        transcript=transcript_path.read_text(encoding="utf-8"),
        hints=args.hints,
        language=args.language,
        model=args.model,
        output_path=metadata_out,
    )
    print(f"[done] 成品: {out_mp3}")
    print(f"[done] metadata: {metadata_out}")
    return 0


# ---------------------------------------------------------------------------
# detect (cough candidate) 模式
# ---------------------------------------------------------------------------


def _cmd_detect(args: argparse.Namespace) -> int:
    input_path: Path = args.input
    if not input_path.exists():
        print(f"錯誤: 音訊檔不存在: {input_path}", file=sys.stderr)
        return 1
    out: Path = args.out or input_path.with_suffix(".mutes.txt")
    detect_cough_candidates(
        input_path=input_path,
        output_path=out,
        high_pass_hz=args.high_pass_hz,
        ratio_threshold=args.ratio,
    )
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yao",
        description="Podcast 混音、自動母帶、中繼資料產生工具",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"yao {__version__}",
    )
    sub = parser.add_subparsers(dest="command", metavar="{auto,detect,mix}")

    # --- auto --------------------------------------------------------------
    p_auto = sub.add_parser(
        "auto",
        help="單檔案自動降噪 + 母帶處理",
        description="對一個原始錄音檔執行: 降噪 → 靜音裁剪 → EQ/壓縮 → 響度 → MP3",
    )
    p_auto.add_argument("input", type=Path, help="原始錄音 (wav/mp3/m4a/flac)")
    p_auto.add_argument(
        "--out", type=Path, default=Path("output"),
        help="輸出目錄 (預設: output/)",
    )
    p_auto.add_argument(
        "--transcript", type=Path,
        help="逐字稿檔案,提供後自動產生 metadata",
    )
    p_auto.add_argument(
        "--mutes", type=Path,
        help="手動靜音範圍檔案 (每行: start end,見 yao detect 產出的樣板)",
    )
    p_auto.add_argument(
        "--hints", default="",
        help="節目主題提示 (metadata 參考)",
    )
    p_auto.add_argument(
        "--language", default="zh-TW",
        help="metadata 輸出語言 (預設: zh-TW)",
    )
    p_auto.add_argument(
        "--model", default="claude-opus-4-6",
        help="Claude 模型 ID",
    )
    p_auto.add_argument(
        "--target-lufs", type=float, default=-16.0,
        help="目標響度 (預設: -16 LUFS)",
    )
    p_auto.add_argument(
        "--denoise-strength", type=float, default=0.8,
        help="降噪強度 0~1 (預設: 0.8)",
    )
    p_auto.add_argument(
        "--max-silence-ms", type=int, default=800,
        help="超過此毫秒數的停頓會被裁剪 (預設: 800)",
    )
    p_auto.add_argument("--no-denoise", action="store_true", help="跳過降噪")
    p_auto.add_argument("--no-trim", action="store_true", help="跳過靜音裁剪")
    p_auto.add_argument("--no-metadata", action="store_true", help="跳過 metadata 產生")

    # --- detect ------------------------------------------------------------
    p_det = sub.add_parser(
        "detect",
        help="偵測咳嗽/突發雜音位置,產出 mutes.txt 樣板",
        description="對原始錄音做瞬態偵測,把候選時間戳寫入文字檔供使用者審閱",
    )
    p_det.add_argument("input", type=Path, help="原始錄音")
    p_det.add_argument(
        "--out", type=Path,
        help="輸出 mutes 檔案路徑 (預設: <input>.mutes.txt)",
    )
    p_det.add_argument(
        "--high-pass-hz", type=float, default=1500.0,
        help="分析用的高通截止頻率 (預設: 1500 Hz)",
    )
    p_det.add_argument(
        "--ratio", type=float, default=5.0,
        help="burst / baseline 比值門檻 (預設: 5.0,越大越保守)",
    )

    # --- mix ---------------------------------------------------------------
    p_mix = sub.add_parser(
        "mix",
        help="使用 YAML 設定檔執行多軌混音",
        description="讀取 YAML 設定,執行人聲 + 音樂 + ducking + intro/outro 的完整混音",
    )
    p_mix.add_argument("config", type=Path)
    p_mix.add_argument("--skip-mix", action="store_true", help="只產生 metadata")
    p_mix.add_argument("--skip-metadata", action="store_true", help="只做混音")

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # 向後相容捷徑: `yao config.yaml` → `yao mix config.yaml`
    if argv and not argv[0].startswith("-") and argv[0] not in {"auto", "detect", "mix"}:
        first = Path(argv[0])
        if first.suffix.lower() in {".yaml", ".yml"}:
            argv = ["mix", *argv]

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "auto":
        return _cmd_auto(args)
    if args.command == "detect":
        return _cmd_detect(args)
    if args.command == "mix":
        return _cmd_mix(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
