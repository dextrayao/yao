# yao

依照你預先寫好（或用 AI 自動生成）的內容，**每天定時自動發兩篇貼文到 [Threads](https://www.threads.net)**。

## 運作方式

```
你寫素材 ──(yao generate, 用 AI 改寫)──▶ 多篇貼文
                                            │
                                            ▼
你也可手動加  ─────(yao add)────────▶  data/queue.json（佇列）
                                            │
                  排程器每天兩個時間各取一篇 │
                                            ▼
                               Threads API（建立 container → 發佈）
```

Threads API 本身**沒有排程功能**，只能立即發佈。這個專案幫你補上「佇列 + 排程器」，到時間了才自動把下一篇發出去。

## 安裝

需要 Node.js 18 以上。

```bash
npm install
cp .env.example .env   # 然後填入你的設定
```

## 設定（.env）

| 變數 | 說明 |
| --- | --- |
| `THREADS_USER_ID` | 你的 Threads 使用者 ID（數字） |
| `THREADS_ACCESS_TOKEN` | Threads API 的長期存取權杖 |
| `SCHEDULE_TIMES` | 每天發文時間，逗號分隔。預設 `09:00,21:00`（= 每天兩篇） |
| `TIMEZONE` | 時區，台灣用 `Asia/Taipei` |
| `ANTHROPIC_API_KEY` | 用 `yao generate` 自動生成貼文時才需要 |

### 怎麼拿到 Threads 的 ID 與權杖

1. 到 [developers.facebook.com](https://developers.facebook.com) 建一個 App，加入「Threads API」use case。
2. 完成 OAuth 授權，取得 access token（建議換成 60 天的 long-lived token，並定期 refresh）。
3. 用 `GET https://graph.threads.net/v1.0/me?fields=id` 取得你的 `THREADS_USER_ID`。

## 使用

### 1. 準備內容

**手動加一篇：**

```bash
node bin/yao.js add "今天想分享的一段話…"
```

**或用 AI 把一整批素材自動改寫成多篇貼文：**

把你的素材（草稿、筆記、想法）放進一個文字檔，例如 `material.txt`，然後：

```bash
node bin/yao.js generate material.txt 10
```

會依素材產生 10 篇符合 Threads 字數上限的貼文，自動加進佇列。

**檢視佇列：**

```bash
node bin/yao.js list
```

### 2. 啟動排程器

```bash
npm start
```

排程器會常駐，每天在 `SCHEDULE_TIMES` 設定的兩個時間，各取一篇待發貼文發出。

### 立刻發一篇（測試用）

```bash
node bin/yao.js publish-now
```

這個指令也適合搭配系統 cron 或 GitHub Actions：不想讓程式一直常駐的話，改用排程器在指定時間呼叫 `yao publish-now` 即可。

## 測試

```bash
npm test
```
