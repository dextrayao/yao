"""Map between timesheet nicknames and Notion salary-table full names."""

NICKNAME_TO_FULLNAME: dict[str, str] = {
    "舒帆": "楊舒帆",
    "子凌": "魏子凌",
    "竩婷": "高誼婷",
    "誼婷": "高誼婷",
    "芸瑩": "蘇芸瑩",
    "旅歐": "林旅歐",
    "興宜": "陳興宜",
    "妤宣": "陳妤宣",
    "靜柔": "李靜柔",
    "珈楨": "吳珈禎",
    "珈禎": "吳珈禎",
    "依軒": "蔡依軒",
    "志欽": "吳志欽",
    "Kevin": "吳志欽",
    "kevin": "吳志欽",
    "素瑜": "李素瑜",
    "冠宇": "蘇冠宇",
    "灝泓": "余灝泓",
    "佩妤": "蔡佩妤",
    "秉熙": "林秉熙",
    "亞軒": "蔡亞軒",
    "明熙": "丁明熙",
    "詩敏": "張詩敏",
    "玟瑄": "陳玟瑄",
    "俐伶": "劉俐伶",
    "芳伃": "周芳伃",
    "育稚": "周育稚",
    "君瑩": "莊君瑩",
    "靜儀": "林靜儀",
    "富美": "葉富美",
    "文劭": "王文劭",
    "元昌": "姚元昌",
    "昱均": "吳昱均",
    "慶文": "顏慶文",
}


def resolve(nickname: str) -> str | None:
    """Return full name for a timesheet nickname, or None if unknown.

    Handles whitespace and accepts full names passing through unchanged
    if already present as a value.
    """
    if not nickname:
        return None
    key = nickname.strip()
    if key in NICKNAME_TO_FULLNAME:
        return NICKNAME_TO_FULLNAME[key]
    if key in NICKNAME_TO_FULLNAME.values():
        return key
    return None
