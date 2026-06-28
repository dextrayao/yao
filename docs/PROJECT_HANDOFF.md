# 專案彙整與交接：Pinterest 圖像逆向 Prompt 分析器

> 給新計畫當起點用的整理。本專案已可運作，第二個逆向模型由 **Gemini 改為「AI 工房」**（OpenAI 相容、支援看圖）。

## 1. 目標

自動抓 Pinterest 圖片 → 用兩個視覺模型逆向推回生成 prompt → 交叉驗證信心分數 → 高正確性者寫入既有 Notion「圖像分析資料庫」。

## 2. 架構與資料流

```
Pinterest 看板/使用者 URL
        │  scraper.py（Playwright 捲動載入，抽高解析圖 + 來源連結）
        ▼
   每張圖下載 (analyzer.download_image)
        │
        ├── Claude (Opus 4.8)        逆向 → prompt / 風格標籤 / 自評信心
        ├── AI 工房 (OpenAI 相容看圖) 逆向 → prompt / 風格標籤 / 自評信心
        └── Claude 裁判交叉比對       → 一致性 agreement + 合成 prompt
        ▼
   verifier.py：最終信心 = agreement × 兩模型平均自評信心
        │  ≥ 門檻（預設 0.75）才通過
        ▼
   notion_writer.py：依「來源出處」去重後寫入 Notion
```

## 3. 模組職責

| 檔案 | 職責 | 對外接口 |
|---|---|---|
| `config.py` | 讀環境變數 + Notion 允許值（select/multi_select 清單） | `config`、`ALLOWED_*` |
| `src/models.py` | 資料結構 | `Pin / Analysis / Validation / Record` |
| `src/scraper.py` | Pinterest 抓取（Playwright，含尺寸→originals、後備選擇器、登入 cookie） | `scrape(url)` |
| `src/analyzer.py` | 雙模型逆向 + Claude 裁判 | `analyze_with_claude`、`analyze_with_workshop`、`cross_validate` |
| `src/verifier.py` | 門檻判斷 | `passes(validation, threshold)` |
| `src/notion_writer.py` | 組 payload、去重、建立頁面 | `build_properties`、`NotionWriter` |
| `src/main.py` | CLI 編排（dry-run / 門檻 / 多來源） | `python -m src.main` |
| `tests/test_logic.py` | 純邏輯單元測試（9 項，不需網路/金鑰） | — |

## 4. Notion「圖像分析資料庫」schema

data source id：`e771e46f-f611-405c-8651-432aae03ba11`

| 欄位 | 類型 | 寫入內容 | 允許值 |
|---|---|---|---|
| 名稱 | title | 裁判合成的中文短名稱 | — |
| 原圖 | file | Pinterest 原圖外連 | — |
| 來源出處 | text | pin 頁面網址（**去重鍵**） | — |
| 逆向 Prompt | text | 合成後的英文 prompt | — |
| 產業用途 | select | 模型分類 | 房地產 / 節慶 |
| 類別 | select | 模型分類 | 社群貼圖 |
| 風格標籤 | multi_select | 模型挑選 | 莫蘭迪綠、漸層背景、顆粒質感、襯線標題、植物線描、幾何疊加、大留白 |
| 備註 | text | 信心分數、一致性、各模型自評、分歧說明 | — |

> 三個受限欄位的允許值定義在 `config.py` 的 `ALLOWED_*`，必須與 Notion 後台一致；模型輸出不在清單內的值會被丟棄。

## 5. AI 工房接入（取代 Gemini 的重點）

- 介面假設為 **OpenAI 相容** `POST {base_url}/chat/completions`，訊息含 `image_url`（base64 data URI）。
- 設定三個環境變數：`AI_WORKSHOP_API_KEY`、`AI_WORKSHOP_BASE_URL`、`AI_WORKSHOP_MODEL`。
- **若工房是私有格式**：只要改 `src/analyzer.py` 的 `analyze_with_workshop()` 一個函式（請求組裝 + 回應取 content），其餘流程（裁判、驗證、寫入）完全不動。
- 回應必須讓模型吐出 `_ANALYZE_INSTRUCTION` 指定的 JSON（name / prompt / industry / category / style_tags / confidence / reasoning）。

## 6. 設定與執行

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env        # 填金鑰

# 試跑不寫入
python -m src.main https://www.pinterest.com/dextrayao/ --dry-run
# 正式寫入，限 20 張、門檻 0.8
python -m src.main https://www.pinterest.com/dextrayao/my-board/ --max-pins 20 --threshold 0.8

python -m pytest tests/ -q
```

需要金鑰：`ANTHROPIC_API_KEY`、`AI_WORKSHOP_*`、`NOTION_API_KEY`、`NOTION_DATABASE_ID`。
Notion 整合要在「圖像分析資料庫」頁面 `···` → 連線 加入該 integration，否則寫不進去。

## 7. 驗證機制

最終信心 `final_confidence = agreement × mean(兩模型自評信心)`，由 `verifier.passes` 與門檻比較。沒有 prompt 一律不過。門檻可用 `--threshold` 或 `CONFIDENCE_THRESHOLD` 調整。

## 8. 風險與待辦

- **Pinterest 抓取脆弱**：無公開 API、會擋自動化。已用主選擇器 + 後備選擇器；改版時需調整 `scraper._extract_pins`。私人看板要設 `PINTEREST_STORAGE_STATE`。
- **AI 工房規格未確認**：目前假設 OpenAI 相容；若不同需改 `analyze_with_workshop`。
- **成本**：每張圖 = Claude 看圖 ×1 + 工房看圖 ×1 + Claude 裁判 ×1（共 3 次推論）。量大可考慮裁判改輕量模型或抽樣。
- **可選強化**：原圖改成上傳 Notion 檔案（而非外連）、加入重試/速率限制、把已處理 pin 存本地避免重抓。
```
