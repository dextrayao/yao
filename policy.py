"""政策參數接口 — 預留未來串接爬蟲抓取最新免稅額與補貼政策"""


def fetch_latest_policy() -> dict:
    """取得最新政策參數。

    目前回傳 2026 年手動設定的預設值。
    未來可改為爬蟲抓取政府公告資料。

    Returns:
        dict: 包含稅務與補貼相關參數
    """
    return {
        "tax": {
            "exemption": 101_000,
            "standard_deduction": 136_000,
            "salary_deduction": 227_000,
            "rent_deduction_cap": 180_000,
            "brackets": [
                (0, 590_000, 0.05),
                (590_000, 1_330_000, 0.12),
                (1_330_000, 2_660_000, 0.20),
                (2_660_000, 4_980_000, 0.30),
                (4_980_000, float("inf"), 0.40),
            ],
        },
        "subsidy": {
            "base_monthly_taipei": 5_000,
            "child_multiplier": 2.0,
        },
        "retirement": {
            "labor_insurance_pension": 26_000,
            "labor_retirement_monthly": 13_500,
        },
    }
