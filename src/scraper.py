"""Pinterest 抓取：以 Playwright 開看板／使用者頁面，捲動載入並抽出 pin。

支援：
- 看板 URL： https://www.pinterest.com/<user>/<board>/
- 使用者 URL：https://www.pinterest.com/<user>/  （抓該帳號近期 pin）
私人看板請設定 PINTEREST_STORAGE_STATE（Playwright 登入後存的 storage_state JSON）。
"""
from __future__ import annotations

import re
from typing import List

from config import config
from src.models import Pin

# i.pinimg.com 的圖片網址帶有尺寸資料夾 (例如 /236x/, /564x/, /60x60_RS/)，
# 換成 /originals/ 可拿到最高解析度。
_SIZE_DIR = re.compile(r"/(\d+x\d*|\d+x)(?:_[A-Z]+)?/")


def upscale_image_url(url: str) -> str:
    """把縮圖網址轉成原圖網址。"""
    return _SIZE_DIR.sub("/originals/", url, count=1)


def normalize_user_url(url: str) -> str:
    """把可能的短網址 / 缺斜線補正。"""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://www.pinterest.com/" + url.lstrip("/")
    if not url.endswith("/"):
        url += "/"
    return url


def scrape(
    url: str,
    max_pins: int | None = None,
    scroll_rounds: int | None = None,
) -> List[Pin]:
    """抓取單一看板／使用者頁面，回傳去重後的 Pin 清單。"""
    max_pins = max_pins or config.max_pins
    scroll_rounds = scroll_rounds or config.scroll_rounds
    url = normalize_user_url(url)

    from playwright.sync_api import sync_playwright

    seen: dict[str, Pin] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context_kwargs = {
            "viewport": {"width": 1280, "height": 1600},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        }
        if config.pinterest_storage_state:
            context_kwargs["storage_state"] = config.pinterest_storage_state

        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(3_000)

        for _ in range(scroll_rounds):
            for pin in _extract_pins(page):
                if pin.image_url not in seen:
                    seen[pin.image_url] = pin
            if len(seen) >= max_pins:
                break
            page.mouse.wheel(0, 4_000)
            page.wait_for_timeout(2_000)

        context.close()
        browser.close()

    return list(seen.values())[:max_pins]


def _extract_pins(page) -> List[Pin]:
    """從目前 DOM 抽出 pin（圖片網址 + 來源連結 + 標題）。"""
    raw = page.eval_on_selector_all(
        "div[data-test-id='pin'], div[data-test-id='pinWrapper']",
        """nodes => nodes.map(n => {
            const img = n.querySelector('img');
            const a = n.querySelector("a[href*='/pin/']");
            return img ? {
                src: img.src,
                alt: img.alt || '',
                href: a ? a.href : ''
            } : null;
        }).filter(Boolean)""",
    )
    # 後備：若上面的選擇器抓不到（Pinterest 改版），退而求其次掃所有 pin 連結。
    if not raw:
        raw = page.eval_on_selector_all(
            "a[href*='/pin/'] img",
            """imgs => imgs.map(img => ({
                src: img.src,
                alt: img.alt || '',
                href: img.closest("a[href*='/pin/']")?.href || ''
            }))""",
        )

    pins: List[Pin] = []
    for item in raw:
        src = item.get("src", "")
        if not src or "i.pinimg.com" not in src:
            continue
        pins.append(
            Pin(
                image_url=upscale_image_url(src),
                source_url=item.get("href", "") or page.url,
                title=item.get("alt", ""),
            )
        )
    return pins
