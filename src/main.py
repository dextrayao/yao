"""主流程 CLI：抓取 → 雙模型逆向 → 交叉驗證 → 過門檻寫入 Notion。

範例：
  python -m src.main https://www.pinterest.com/dextrayao/ --max-pins 20
  python -m src.main dextrayao/my-board --dry-run
"""
from __future__ import annotations

import argparse
import sys

from config import config
from src import analyzer, scraper, verifier
from src.models import Record
from src.notion_writer import NotionWriter


def process_pin(pin) -> Record:
    """對單一 pin 跑完整分析與驗證。"""
    image, mime = analyzer.download_image(pin.image_url)
    claude = analyzer.analyze_with_claude(image, mime)
    workshop = analyzer.analyze_with_workshop(image, mime)
    validation = analyzer.cross_validate(image, mime, claude, workshop)
    return Record(pin=pin, claude=claude, workshop=workshop, validation=validation)


def run(urls: list[str], dry_run: bool, threshold: float, max_pins: int | None) -> int:
    config.require("anthropic_api_key", "workshop_api_key", "workshop_base_url", "workshop_model")
    if not dry_run:
        config.require("notion_api_key", "notion_database_id")
        writer = NotionWriter()

    saved = skipped = failed = 0

    for url in urls:
        print(f"\n=== 抓取 {url} ===")
        pins = scraper.scrape(url, max_pins=max_pins)
        print(f"找到 {len(pins)} 張圖")

        for i, pin in enumerate(pins, 1):
            try:
                record = process_pin(pin)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"  [{i}] 分析失敗：{exc}")
                continue

            v = record.validation
            ok = verifier.passes(v, threshold)
            mark = "✅" if ok else "✋"
            print(f"  [{i}] {mark} {v.name or pin.title!r} 信心={v.final_confidence} "
                  f"(一致性={v.agreement}) tags={v.style_tags}")

            if not ok:
                skipped += 1
                continue

            if dry_run:
                print(f"      [dry-run] prompt: {v.prompt[:120]}...")
                saved += 1
                continue

            if writer.exists(pin.source_url):
                print("      已存在，略過")
                skipped += 1
                continue

            writer.create(record)
            saved += 1
            print("      已寫入 Notion")

    print(f"\n完成：寫入 {saved}、略過 {skipped}、失敗 {failed}"
          + ("（dry-run 未實際寫入）" if dry_run else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pinterest 圖像逆向 Prompt 分析 → Notion")
    parser.add_argument("urls", nargs="+", help="Pinterest 看板或使用者 URL（可多個）")
    parser.add_argument("--dry-run", action="store_true", help="只分析印出，不寫入 Notion")
    parser.add_argument("--threshold", type=float, default=config.confidence_threshold,
                        help="信心分數門檻 (預設取自設定)")
    parser.add_argument("--max-pins", type=int, default=None, help="每個來源最多抓幾張")
    args = parser.parse_args(argv)

    return run(args.urls, args.dry_run, args.threshold, args.max_pins)


if __name__ == "__main__":
    sys.exit(main())
