"""網頁介面：Pinterest 網址 或 手動上傳圖檔 → 逆向分析 → 過門檻寫入 Notion。

啟動：
    streamlit run app.py
"""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from config import config
from src import scraper, verifier
from src.main import analyze_record, process_pin
from src.models import Pin
from src.notion_writer import NotionWriter

st.set_page_config(page_title="圖像逆向 Prompt 分析器", page_icon="📌", layout="wide")
st.title("📌 圖像逆向 Prompt 分析器")
st.caption("貼 Pinterest 網址、或直接上傳圖檔，自動反推生成 prompt，過門檻者寫入 Notion。")


def _flag(ok: bool) -> str:
    return "✅" if ok else "❌"


_MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
         "webp": "image/webp", "gif": "image/gif"}

workshop_ready = bool(config.workshop_api_key and config.workshop_base_url and config.workshop_model)
notion_ready = bool(config.notion_api_key and config.notion_database_id)

with st.sidebar:
    st.header("設定狀態")
    st.write(f"{_flag(workshop_ready)} AI 工房（本機 Ollama，免費必備）")
    claude_on = bool(config.anthropic_api_key)
    st.write(f"{_flag(claude_on)} Claude（選用，加強驗證會用額度）")
    st.write(f"{_flag(notion_ready)} Notion（要寫入才需要）")
    if claude_on:
        st.caption("目前：雙模型交叉驗證（品質高，會用 Claude 額度）")
    else:
        st.caption("目前：免費單模型模式（只用本機 Ollama，零 token 成本）")

mode = st.radio("圖片來源", ["手動上傳圖檔", "Pinterest 網址"], horizontal=True)

url = ""
uploads = []
if mode == "Pinterest 網址":
    url = st.text_input("Pinterest 看板 / 使用者 URL",
                        placeholder="https://www.pinterest.com/dextrayao/ 或 dextrayao/某看板")
else:
    uploads = st.file_uploader(
        "把圖檔拖進來（可一次多張）", type=list(_MIME.keys()), accept_multiple_files=True
    )

c1, c2, c3 = st.columns(3)
max_pins = c1.number_input("最多抓幾張（僅 Pinterest）", min_value=1, max_value=200, value=config.max_pins)
threshold = c2.slider("信心門檻", 0.0, 1.0, float(config.confidence_threshold), 0.05)
dry_run = c3.checkbox("試跑（不寫入 Notion）", value=True)

ready_to_run = bool(url.strip()) if mode == "Pinterest 網址" else bool(uploads)
start = st.button("開始分析", type="primary", disabled=not ready_to_run)


@dataclass
class _Job:
    """一張待分析的圖：要嘛有網址（Pinterest），要嘛有 bytes（上傳）。"""
    pin: Pin
    image: bytes | None = None
    mime: str = ""


def _collect_jobs() -> list[_Job]:
    if mode == "Pinterest 網址":
        pins = scraper.scrape(url, max_pins=int(max_pins))
        return [_Job(pin=p) for p in pins]
    jobs = []
    for f in uploads:
        ext = f.name.rsplit(".", 1)[-1].lower()
        jobs.append(_Job(
            pin=Pin(image_url="", source_url=f"手動上傳:{f.name}", title=f.name),
            image=f.getvalue(),
            mime=_MIME.get(ext, "image/jpeg"),
        ))
    return jobs


if start:
    missing = []
    if not workshop_ready:
        missing.append("AI 工房（本機 Ollama）")
    if not dry_run and not notion_ready:
        missing.append("Notion")
    if missing:
        st.error("缺少設定：" + "、".join(missing) + "。請先在 .env 填好金鑰。")
        st.stop()

    writer = None if dry_run else NotionWriter()

    with st.status("準備圖片…", expanded=True) as status:
        try:
            jobs = _collect_jobs()
        except Exception as exc:  # noqa: BLE001
            status.update(label="取得圖片失敗", state="error")
            st.exception(exc)
            st.stop()
        st.write(f"共 {len(jobs)} 張圖，開始分析…")
        if not jobs:
            status.update(label="沒有圖片可分析", state="error")
            st.warning("沒有圖片。Pinterest 模式請確認網址；上傳模式請先選檔。")
            st.stop()
        status.update(label=f"分析 {len(jobs)} 張圖…")

    saved = skipped = failed = 0
    progress = st.progress(0.0)

    for i, job in enumerate(jobs, 1):
        progress.progress(i / max(len(jobs), 1))
        try:
            if job.image is not None:                     # 手動上傳
                record = analyze_record(job.pin, job.image, job.mime)
            else:                                         # Pinterest
                record = process_pin(job.pin)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            st.warning(f"第 {i} 張分析失敗：{exc}")
            continue

        v = record.validation
        passed = verifier.passes(v, threshold)

        wrote = False
        if passed and not dry_run:
            if writer.exists(job.pin.source_url):
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
        with st.expander(f"[{i}] {v.name or job.pin.title or '未命名'} — {badge}（信心 {v.final_confidence}）"):
            cols = st.columns([1, 2])
            if job.image is not None:
                cols[0].image(job.image, use_container_width=True)
            elif job.pin.image_url:
                cols[0].image(job.pin.image_url, use_container_width=True)
            cols[1].markdown(f"**逆向 Prompt**\n\n{v.prompt or '—'}")
            cols[1].write({
                "信心分數": v.final_confidence,
                "一致性": v.agreement,
                "產業用途": v.industry,
                "類別": v.category,
                "風格標籤": v.style_tags,
                "來源出處": job.pin.source_url,
            })
            if v.notes:
                cols[1].caption(v.notes)

    progress.empty()
    msg = f"完成：通過 {saved}、略過 {skipped}、失敗 {failed}"
    if dry_run:
        msg += "（試跑，未寫入 Notion）"
    st.success(msg)
