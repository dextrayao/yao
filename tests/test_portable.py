"""單檔 pinterest_to_notion.py 的純邏輯測試（不需網路/金鑰）。"""
import importlib.util
import os
import pathlib
import sys

import pytest

_PATH = pathlib.Path(__file__).resolve().parent.parent / "pinterest_to_notion.py"
_spec = importlib.util.spec_from_file_location("pinterest_to_notion", _PATH)
ptn = importlib.util.module_from_spec(_spec)
sys.modules["pinterest_to_notion"] = ptn  # dataclass 需能在 sys.modules 找到自身
_spec.loader.exec_module(ptn)


def test_parse_json_robust():
    assert ptn._parse_json('{"a": 1}') == {"a": 1}
    assert ptn._parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    # 圍欄外才是真 JSON —— 不可被丟掉
    assert ptn._parse_json('see ```x``` then {"a": 1}') == {"a": 1}
    with pytest.raises(ValueError):
        ptn._parse_json("沒有 JSON")


def test_env_numeric_tolerant():
    os.environ["CONFIDENCE_THRESHOLD"] = "oops"
    try:
        assert ptn._env_float("CONFIDENCE_THRESHOLD", 0.75) == 0.75
        assert ptn._env_int("NOPE_VAR", 7) == 7
    finally:
        os.environ.pop("CONFIDENCE_THRESHOLD", None)


def test_upscale_and_passes():
    assert ptn.upscale_image_url("https://i.pinimg.com/236x/a/b.jpg") == \
        "https://i.pinimg.com/originals/a/b.jpg"
    v_ok = ptn.Validation(name="n", prompt="p", industry=None, category=None,
                          style_tags=[], agreement=0.9, final_confidence=0.8)
    v_no = ptn.Validation(name="n", prompt="", industry=None, category=None,
                          style_tags=[], agreement=0.9, final_confidence=0.99)
    assert ptn.passes(v_ok, threshold=0.75) is True
    assert ptn.passes(v_no, threshold=0.5) is False


def test_build_properties_parity():
    pin = ptn.Pin(image_url="https://i.pinimg.com/originals/a/b.jpg",
                  source_url="https://www.pinterest.com/pin/1/", title="t")
    v = ptn.Validation(name="客廳", prompt="a room", industry="房地產",
                       category="社群貼圖", style_tags=["大留白"],
                       agreement=0.9, final_confidence=0.82)
    rec = ptn.Record(pin=pin, claude=ptn.Analysis(model="claude", confidence=0.9),
                     workshop=ptn.Analysis(model="workshop", confidence=0.8), validation=v)
    props = ptn.build_properties(rec)
    assert props["產業用途"]["select"]["name"] == "房地產"
    assert props["風格標籤"]["multi_select"][0]["name"] == "大留白"
