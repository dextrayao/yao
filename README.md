# Pinterest 圖像逆向 Prompt 分析器

自動抓取 Pinterest 看板／使用者頁面的圖片，用 **Claude + AI 工房雙模型**逆向推回生成 prompt，經**交叉驗證信心分數**篩選後，把高正確性的結果寫入既有的 Notion「圖像分析資料庫」。

## 流程

```
Pinterest 看板/使用者 URL
        │  scraper.py (Playwright 捲動載入，抽出高解析圖 + 來源連結)
        ▼
   每張圖下載
        │  analyzer.py
        ├── Claude (Opus 4.8) 逆向 → prompt / 風格標籤 / 自評信心
        ├── AI 工房逆向          → prompt / 風格標籤 / 自評信心（OpenAI 相容看圖）
        └── Claude 裁判交叉比對  → 一致性 agreement + 合成 prompt
        ▼
   verifier.py：最終信心 = 一致性 × 兩模型平均自評信心
        │  ≥ 門檻 (預設 0.75) 才通過
        ▼
   notion_writer.py：依「來源出處」去重後寫入 Notion
```

## 安裝

```bash
pip install -r requirements.txt
playwright install chromium      # 安裝瀏覽器（首次）
cp .env.example .env             # 填入金鑰
```

需要的金鑰見 `.env.example`：`ANTHROPIC_API_KEY`、`AI_WORKSHOP_API_KEY`/`AI_WORKSHOP_BASE_URL`/`AI_WORKSHOP_MODEL`、`NOTION_API_KEY`、`NOTION_DATABASE_ID`。

> Notion 整合：到 <https://www.notion.so/my-integrations> 建立 internal integration，
> 並在「圖像分析資料庫」頁面右上 `···` → 連線 → 加入該整合。

## 使用

```bash
# 抓某使用者近期 pin，先試跑不寫入
python -m src.main https://www.pinterest.com/dextrayao/ --dry-run

# 抓特定看板，最多 20 張，過門檻就寫入 Notion
python -m src.main https://www.pinterest.com/dextrayao/my-board/ --max-pins 20

# 調整門檻、多個來源
python -m src.main dextrayao/board-a dextrayao/board-b --threshold 0.8
```

私人看板：先用 Playwright 登入存出 `storage_state`，把路徑填到 `.env` 的 `PINTEREST_STORAGE_STATE`。

## 對應的 Notion 欄位

| Notion 欄位 | 來源 |
|---|---|
| 名稱 | 裁判合成的中文短名稱 |
| 原圖 | Pinterest 原圖外連 |
| 來源出處 | pin 頁面網址（去重鍵）|
| 逆向 Prompt | 合成後的英文 prompt |
| 產業用途／類別 | 模型分類（限既有選項）|
| 風格標籤 | 模型挑選（限既有選項）|
| 備註 | 信心分數、一致性、模型分歧說明 |

風格標籤 / 產業用途 / 類別的允許值定義在 `config.py`，必須與 Notion 後台選項一致。

## 測試

```bash
python -m pytest tests/ -q
```

純邏輯（門檻判斷、標籤過濾、Notion payload）皆有單元測試，不需網路或金鑰。
