# 部署到 Mac Studio

AI 工房（看圖模型）就跑在這台 Mac Studio 上，把本工具裝在同一台最順——同機呼叫工房，網頁介面也在這開。

## 一鍵安裝

```bash
git clone https://github.com/dextrayao/yao.git
cd yao
git checkout claude/pinterest-image-prompt-analyzer-ro0toj
bash deploy/setup_macstudio.sh
```

腳本會：建立 `venv`、裝套件、裝 Playwright Chromium、複製 `.env`，並**自動探測 AI 工房列出可用模型**。

## 填 `.env`

`AI_WORKSHOP_BASE_URL` 已預設為 `https://macmac-studio.tailbfceaf.ts.net/v1`。還需填：

- `ANTHROPIC_API_KEY`
- `AI_WORKSHOP_MODEL`（從探測結果挑一個看得懂圖的）
- `NOTION_API_KEY`、`NOTION_DATABASE_ID`

隨時可重跑探測：

```bash
source venv/bin/activate
python deploy/detect_workshop.py
```

## 啟動

```bash
bash deploy/run.sh          # 只在本機開：http://localhost:8501
bash deploy/run.sh --lan    # 對 Tailscale/區網開放：http://macmac-studio:8501
```

## 開機自動常駐（選用）

把 `com.kuke.pinterest-analyzer.plist` 裡的 `__PROJECT_DIR__` 改成專案絕對路徑後：

```bash
cp deploy/com.kuke.pinterest-analyzer.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.kuke.pinterest-analyzer.plist
```

之後 Mac Studio 一開機，網頁介面就自動跑起來。

## 疑難排解

- **探測連不上**：確認工房伺服器有開、Tailscale 正常、`AI_WORKSHOP_BASE_URL` 結尾是 `/v1`。
- **逆向分析失敗**：`AI_WORKSHOP_MODEL` 必須是**多模態/看圖**模型（如 Qwen2-VL、Llama 3.2 Vision、MiniCPM-V、LLaVA）。
- **抓不到 Pinterest 私人看板**：用 Playwright 登入存 `storage_state`，路徑填 `.env` 的 `PINTEREST_STORAGE_STATE`。
