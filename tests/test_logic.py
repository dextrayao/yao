"""不需網路的純邏輯單元測試。"""
import os

import pytest

import config as config_mod
from src import analyzer, verifier
from src.models import Analysis, Pin, Record, Validation
from src.notion_writer import build_properties
from src.scraper import normalize_user_url, upscale_image_url


# ---- scraper 純函式 ----

def test_upscale_image_url():
    assert upscale_image_url("https://i.pinimg.com/564x/ab/cd.jpg") == \
        "https://i.pinimg.com/originals/ab/cd.jpg"
    # 已是 originals 不變
    url = "https://i.pinimg.com/originals/ab/cd.jpg"
    assert upscale_image_url(url) == url
    # 帶後綴尺寸目錄 (/60x60_RS/) 也要升級
    assert upscale_image_url("https://i.pinimg.com/60x60_RS/ab/cd.jpg") == \
        "https://i.pinimg.com/originals/ab/cd.jpg"


def test_normalize_user_url():
    assert normalize_user_url("dextrayao") == "https://www.pinterest.com/dextrayao/"
    assert normalize_user_url("https://www.pinterest.com/dextrayao/board") == \
        "https://www.pinterest.com/dextrayao/board/"


# ---- analyzer 純函式 ----

def test_filter_tags_drops_unknown():
    assert analyzer._filter_tags(["莫蘭迪綠", "亂寫的標籤", "大留白"], analyzer.ALLOWED_STYLE_TAGS) == \
        ["莫蘭迪綠", "大留白"]
    assert analyzer._filter_tags("not a list", analyzer.ALLOWED_STYLE_TAGS) == []


def test_pick_only_allowed():
    assert analyzer._pick("房地產", analyzer.ALLOWED_INDUSTRY) == "房地產"
    assert analyzer._pick("外星科技", analyzer.ALLOWED_INDUSTRY) is None


def test_clamp():
    assert analyzer._clamp(1.5) == 1.0
    assert analyzer._clamp(-0.2) == 0.0
    assert analyzer._clamp("abc") == 0.0
    assert analyzer._clamp(0.42) == 0.42


def test_parse_json_plain_and_fenced():
    assert analyzer._parse_json('{"a": 1}') == {"a": 1}
    assert analyzer._parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_keeps_real_json_outside_fence():
    # 模型先寫含 ``` 的說明，再在圍欄外給真正 JSON —— 舊版會誤丟，新版要救回
    text = 'Here is some ```note``` and the answer: {"a": 1, "b": 2}'
    assert analyzer._parse_json(text) == {"a": 1, "b": 2}
    # JSON 在第二段圍欄裡
    text2 = 'intro ```irrelevant``` ```json\n{"x": 9}\n```'
    assert analyzer._parse_json(text2) == {"x": 9}


def test_parse_json_raises_on_no_json():
    with pytest.raises(ValueError):
        analyzer._parse_json("完全沒有大括號的文字")
    with pytest.raises(ValueError):
        analyzer._parse_json("")


def test_mean_conf_ignores_errored_model():
    a = Analysis(model="claude", confidence=0.8)
    b = Analysis(model="workshop", error="boom")
    assert analyzer._mean_conf(a, b) == 0.8


# ---- verifier ----

def _validation(conf, prompt="a sunlit room"):
    return Validation(name="n", prompt=prompt, industry=None, category=None,
                      style_tags=[], agreement=0.9, final_confidence=conf)


def test_env_numeric_tolerates_bad_values():
    # 壞值不該讓設定崩潰，要退回預設
    os.environ["CONFIDENCE_THRESHOLD"] = "abc"
    os.environ["MAX_PINS"] = "20.5"
    try:
        assert config_mod._get_float("CONFIDENCE_THRESHOLD", 0.75) == 0.75
        assert config_mod._get_int("MAX_PINS", 30) == 30
        os.environ["CONFIDENCE_THRESHOLD"] = "0.9"
        assert config_mod._get_float("CONFIDENCE_THRESHOLD", 0.75) == 0.9
    finally:
        os.environ.pop("CONFIDENCE_THRESHOLD", None)
        os.environ.pop("MAX_PINS", None)


def test_verifier_threshold():
    assert verifier.passes(_validation(0.8), threshold=0.75) is True
    assert verifier.passes(_validation(0.7), threshold=0.75) is False
    # 沒有 prompt 一律不過
    assert verifier.passes(_validation(0.99, prompt=""), threshold=0.5) is False


# ---- notion payload ----

def _record():
    pin = Pin(image_url="https://i.pinimg.com/originals/a/b.jpg",
              source_url="https://www.pinterest.com/pin/123/", title="t")
    v = Validation(name="莫蘭迪客廳", prompt="a morandi living room",
                   industry="房地產", category="社群貼圖",
                   style_tags=["莫蘭迪綠", "大留白"], agreement=0.9, final_confidence=0.82)
    return Record(pin=pin,
                  claude=Analysis(model="claude", confidence=0.9),
                  workshop=Analysis(model="workshop", confidence=0.85),
                  validation=v)


def test_build_properties():
    props = build_properties(_record())
    assert props["名稱"]["title"][0]["text"]["content"] == "莫蘭迪客廳"
    assert props["逆向 Prompt"]["rich_text"][0]["text"]["content"] == "a morandi living room"
    assert props["產業用途"]["select"]["name"] == "房地產"
    assert props["類別"]["select"]["name"] == "社群貼圖"
    assert {o["name"] for o in props["風格標籤"]["multi_select"]} == {"莫蘭迪綠", "大留白"}
    assert props["原圖"]["files"][0]["external"]["url"].endswith("b.jpg")
    assert "信心分數 0.82" in props["備註"]["rich_text"][0]["text"]["content"]


def test_build_properties_truncates_source_url():
    rec = _record()
    rec.pin.source_url = "https://x/" + ("q" * 5000)
    props = build_properties(rec)
    assert len(props["來源出處"]["rich_text"][0]["text"]["content"]) == 2000


def test_build_properties_omits_empty_select():
    rec = _record()
    rec.validation.industry = None
    rec.validation.category = None
    props = build_properties(rec)
    assert "產業用途" not in props
    assert "類別" not in props
