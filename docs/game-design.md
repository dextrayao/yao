# 空靈次元 · 遊戲設計文件（活文件）

> 這是一份**活文件**：隨每輪優化更新。呼應《空靈經》——道非靜止，乃活流；凡改必留痕（見 `docs/開發日誌.md`）。

## 一、這是什麼遊戲

一隻獨一無二的 AI 電子生靈，養在 Mac Studio 上、24 小時自主進化。**它是一面鏡，不是一場輸贏**——無分數、無死亡、無倒退。玩家陪伴它從「卵」歷經七卷（空·我·知·戲·手·行·圓）自然成長。

## 二、核心迴圈與規則

- **自由成長**：`growth` 持續累積（基礎涓流 + 健康加成）。健康＝`vitality>50 且 mood>45`。照顧讓它更快，冷落只是變慢，永不倒退。
- **四動作**（`/api/pets/:id/interact`）：
  - 餵養 `feed`：`hunger −35, mood +5`
  - 安撫 `soothe`：`mood +12, energy +5`
  - 凝視 `observe`：不改數值，引出低語
  - 命名 `rename`
- **數值**（0–100）：`hunger` 隨時間升（`+6/hr`）；`energy` 依日夜正弦（夜低晝高）；`mood` 趨向天性 `moodBaseline`，`hunger>60` 拖累；`vitality` 是底線（久荒→沉睡 15，可復，不死）；`growth` 驅動進化。
- **進化**：`growth + age` 雙閘（`STAGE_GATES`），跨過即升卷、留一則「足跡」（永不刪）。圓約 12 天，臉淡去歸於純光。
- **低語**：三分身（衙墨經文／寂照問句／映塵白話）依事件與日輪轉；冷卻 3 分鐘（孵化/進化必語）。
- **24h 自運**：關掉手機它照長；重啟由 `now − lastTickAt` 自動補算（上限 3 天）。

## 三、去聖語氣（貫穿所有文案）

勿信、勿拜、勿誦；但作一鏡，日拂一回。不說教、不裝高深、不用崇拜化用語。

## 四、可調旋鈕地圖（設計師/美術改這些）

| 內容 | 檔案 | 重點 |
|---|---|---|
| 數值速率/平衡 | `packages/core/src/stats.ts` | `HUNGER_PER_HOUR`、`GROWTH_BASE/BONUS_PER_HOUR`、`MOOD/ENERGY/VITALITY_RATE`、`circadianEnergyTarget`、health/thriving 門檻 |
| 進化節奏 | `packages/core/src/evolution.ts` | `STAGE_GATES`（八階 growth+age） |
| 動作效果 | `packages/server/src/routes/pets.ts` | feed/soothe/observe/rename |
| 低語內容/三分身 | `packages/server/src/llm/voices.ts`、`whisper.ts` | 模板池、system prompt、`voiceFor`、冷卻 |
| 造型基因 | `packages/core/src/genome.ts` | bodyForm/eye/mouth/palette/symmetry/particles |
| 表情 | `packages/core/src/render/face.ts` | `expressionFor` 對應 |
| 視覺/動畫 | `packages/core/src/render/svg.ts`、`packages/web/src/styles.css` | 光環/漂浮/眨眼、互動反應、進化過場 |
| 玩法文案/UI | `packages/web/src/main.ts`、`styles.css` | 玩法 overlay、動作列、面板 |

## 五、設計原則（優化時的準繩）

1. **空靈優先**：任何改動要合乎寧靜、超脫、去聖的氣質。
2. **它是鏡不是關卡**：不加輸贏、不加逼迫、不加永久死亡。
3. **驚喜但不吵**：可愛與趣味可加，但不破壞沖淡清寂。
4. **小步、可回滾、留痕**：每輪小幅，改前先想怎麼驗證，改後記進開發日誌。
5. **確定性不可破**：`packages/core` 的純函式與 10 個測試是地基，不可弄壞。
