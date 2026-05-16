# 酷客創藝 ・ 專案人力成本週報

每週一早上 05:00 (Asia/Taipei) 由 GitHub Actions 自動拉 Notion 上的人員日薪表 + Google Sheet 上的工作日誌,計算上週每個 **客戶 / 專案** 的完整人力成本,並產出一份 HTML 公開到 GitHub Pages。

成本基準:**完整勞動成本 = 本俸 × 1.2551**(含勞健保/勞退/年終分攤),與 Notion `💰 人力成本分析` 頁口徑一致。

公開網址:`https://dextrayao.github.io/yao/`(啟用 Pages 後生效)

---

## 一次性設定

### 1. Notion Integration

1. 到 https://www.notion.so/profile/integrations 建立一個 **Internal Integration** (名稱例如 `Weekly Labor Cost`)。
2. 拷貝 **Internal Integration Token** → repo Settings → Secrets and variables → Actions → 新增 secret `NOTION_TOKEN`。
3. 打開 [💰 人力成本分析](https://www.notion.so/35898c04256781979640e78aab24874f) 頁面 → 右上 `…` → `Connections` → 新增剛才建立的 Integration。

### 2. Google Service Account

1. 在 https://console.cloud.google.com/iam-admin/serviceaccounts 建立 Service Account。
2. 為它建立 JSON Key,下載整個 JSON 檔。
3. 啟用 `Google Sheets API`(APIs & Services → Library)。
4. 把 JSON **整段內容**設為 GitHub secret `GOOGLE_SA_JSON`。
5. 打開 [工作日誌2026](https://docs.google.com/spreadsheets/d/1cvHG-2urNIZVmNDOBXC88ioWZDN_Q1RkWJO0qNd1_-8) → 右上 `Share` → 把 Service Account 的 email (`xxx@xxx.iam.gserviceaccount.com`) 加為 **Viewer**。

### 3. GitHub Pages

1. Settings → Pages → Source: **Deploy from a branch**
2. Branch: `claude/weekly-labor-cost-tracking-bx5YU` / Folder: **`/docs`**
3. Save → 等 1 分鐘,網址 `https://dextrayao.github.io/yao/` 就會上線。

---

## 手動觸發 / 補跑歷史週

1. GitHub → Actions → `weekly-labor-cost` → **Run workflow**
2. 可填 `week_iso`(格式 `2026-W16`),留空 = 上一個完整週

排程本身固定:`cron: '0 21 * * 0'` (UTC) = 每週一 05:00 Asia/Taipei。

---

## 本機開發

```bash
pip install -r requirements.txt

# 跑單元測試
python -m pytest tests/

# 用 fixture 模擬產生報表(不需要 Notion / Google 憑證)
python -m scripts.weekly_report 2026-W16 \
    --fixture tests/fixtures/week16.csv \
    --salary  tests/fixtures/salary.json \
    --out     /tmp/preview.html
open /tmp/preview.html  # macOS;Linux 用 xdg-open
```

接真實資料(本機跑):

```bash
export NOTION_TOKEN='secret_xxx'
export GOOGLE_SA_JSON="$(cat /path/to/sa.json)"
export SHEET_ID='1cvHG-2urNIZVmNDOBXC88ioWZDN_Q1RkWJO0qNd1_-8'
export SALARY_PAGE_ID='35898c04-2567-8197-9640-e78aab24874f'
python -m scripts.weekly_report                    # 上一個完整週
python -m scripts.weekly_report 2026-W16           # 指定週
```

---

## 專案結構

```
.
├── .github/workflows/weekly-labor-cost.yml   # cron + push
├── scripts/
│   ├── weekly_report.py                      # CLI 入口
│   ├── notion_client.py                      # 拉 Notion 薪資表
│   ├── sheets_client.py                      # 拉 Google Sheets 工時
│   ├── aggregate.py                          # 聚合 + 成本計算
│   ├── render.py                             # Jinja2 渲染
│   └── name_map.py                           # 暱稱 ↔ 全名對應
├── templates/
│   ├── report.html.j2                        # 週報模板
│   ├── index.html.j2                         # 首頁模板
│   └── base.css                              # Claude 風格 design tokens
├── docs/                                     # GitHub Pages 根目錄
│   ├── .nojekyll
│   ├── index.html                            # (自動生成)
│   └── weeks/2026-Wxx.html + .json           # (每週生成)
├── tests/
│   ├── test_aggregate.py
│   ├── test_parse_hours.py
│   └── fixtures/
│       ├── salary.json
│       └── week16.csv
├── requirements.txt
└── README.md
```

---

## 加新員工 / 新暱稱

工作日誌用暱稱(`舒帆`、`旅歐`...),Notion 薪資表用全名(`楊舒帆`、`林旅歐`...)。如果遇到沒對應上的新員工,週報的 **資料品質** 區塊會列出「未對應暱稱」清單。請編輯:

```python
# scripts/name_map.py
NICKNAME_TO_FULLNAME = {
    ...,
    "新暱稱": "新員工全名",
}
```

未對應的工時不會被丟掉 — 會以該部門平均日薪估算成本,保證總額可信。
