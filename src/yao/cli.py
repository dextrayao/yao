"""Yao CLI — 根據 YAML 設定檔執行混音並產生中繼資料。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .metadata import generate_metadata
from .mixer import mix_podcast


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


def _run_metadata(cfg: dict[str, Any]) -> None:
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
    transcript = tpath.read_text(encoding="utf-8")
    result = generate_metadata(
        transcript=transcript,
        hints=str(meta_cfg.get("topic_hints", "")),
        language=str(meta_cfg.get("language", "zh-TW")),
        model=str(meta_cfg.get("model", "claude-opus-4-6")),
    )

    out_path = Path(meta_cfg.get("output_path", "output/metadata.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    usage = result.get("_usage", {})
    print(f"       已輸出 metadata: {out_path}")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="yao",
        description="Podcast 混音與中繼資料產生工具",
    )
    parser.add_argument(
        "config",
        type=Path,
        help="YAML 設定檔路徑 (參考 examples/config.example.yaml)",
    )
    parser.add_argument(
        "--skip-mix",
        action="store_true",
        help="跳過混音,只產生 metadata",
    )
    parser.add_argument(
        "--skip-metadata",
        action="store_true",
        help="跳過 metadata 產生,只做混音",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"yao {__version__}",
    )
    args = parser.parse_args(argv)

    cfg = _load_config(args.config)

    if not args.skip_mix:
        _run_mix(cfg)
    else:
        print("[1/2] 已跳過混音")

    if not args.skip_metadata:
        _run_metadata(cfg)
    else:
        print("[2/2] 已跳過 metadata 產生")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
