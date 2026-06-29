"""網頁介面：貼上 Pinterest 網址 → 一鍵分析 → 過門檻寫入 Notion。

啟動：
    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from config import config
from src import scraper, verifier
from src.main import process_pin
from src.notion_writer import NotionWriter

st.set_page_config(page_title="Pinterest 逆向 Prompt 分析器", page_icon="📌", layout="wide")
st.title("📌 Pinterest 圖像逆向 Prompt 分析器")
st.caption("貼上 Pinterest 看板／使用者網址，自動反推生成 prompt，過門檻者寫入 Notion。")


def _flag(ok: bool) -> str:
    return "✅" if ok else "❌"


workshop_ready = bool(config.workshop_api_key and config.workshop_base_url and config.workshop_model)
notion_ready = bool(config.notion_api_key and config.notion_database_id)

with st.sidebar:
    st.header("設定狀態")
    st.write(f"{_flag(bool(config.anthropic_api_key))} Claude API")
    st.write(f"{_flag(workshop_ready)} AI 工房")
    st.write(f"{_flag(notion_ready)} Notion")
    st.caption("金鑰在專案根目錄的 `.env` 設定（見 .env.example）。")

url = st.text_input(
    "Pinterest 看板 / 使用者 URL",
    placeholder="https://www.pinterest.com/dextrayao/ 或 dextrayao/某看板",
)

c1, c2, c3 = st.columns(3)
max_pins = c1.number_input("最多抓幾張", min_value=1, max_value=200, value=config.max_pins)
threshold = c2.slider("信心門檻", 0.0, 1.0, float(config.confidence_threshold), 0.05)
dry_run = c3.checkbox("試跑（不寫入 Notion）", value=True)

start = st.button("開始分析", type="primary", disabled=not url.strip())

if start:
    missing = []
    if not config.anthropic_api_key:
        missing.append("Claude")
    if not workshop_ready:
        missing.append("AI 工房")
    if not dry_run and not notion_ready:
        missing.append("Notion")
    if missing:
        st.error("缺少設定：" + "、".join(missing) + "。請先在 .env 填好金鑰。")
        st.stop()

    writer = None if dry_run else NotionWriter()

    with st.status("抓取 Pinterest…", expanded=True) as status:
        try:
            pins = scraper.scrape(url, max_pins=int(max_pins))
        except Exception as exc:  # noqa: BLE001
            status.update(label="抓取失敗", state="error")
            st.exception(exc)
            st.stop()
        st.write(f"找到 {len(pins)} 張圖，開始分析…")
        status.update(label=f"分析 {len(pins)} 張圖…")

    saved = skipped = failed = 0
    progress = st.progress(0.0)

    for i, pin in enumerate(pins, 1):
        progress.progress(i / max(len(pins), 1))
        try:
            record = process_pin(pin)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            st.warning(f"第 {i} 張分析失敗：{exc}")
            continue

        v = record.validation
        passed = verifier.passes(v, threshold)

        wrote = False
        if passed and not dry_run:
            if writer.exists(pin.source_url):
                skipped += 1
            else:
                writer.create(record)
                wrote = True
                saved += 1
        elif passed:
            saved += 1
        else:
            skipped += 1

        badge = "✅ 通過" if passed else "✋ 未達門檻"
        if wrote:
            badge += "・已寫入 Notion"
        with st.expander(f"[{i}] {v.name or pin.title or '未命名'} — {badge}（信心 {v.final_confidence}）"):
            cols = st.columns([1, 2])
            if pin.image_url:
                cols[0].image(pin.image_url, use_container_width=True)
            cols[1].markdown(f"**逆向 Prompt**\n\n{v.prompt or '—'}")
            cols[1].write(
                {
                    "信心分數": v.final_confidence,
                    "一致性": v.agreement,
                    "產業用途": v.industry,
                    "類別": v.category,
                    "風格標籤": v.style_tags,
                    "來源出處": pin.source_url,
                }
            )
            if v.notes:
                cols[1].caption(v.notes)

    progress.empty()
    msg = f"完成：通過 {saved}、略過 {skipped}、失敗 {failed}"
    if dry_run:
        msg += "（試跑，未寫入 Notion）"
    st.success(msg)
