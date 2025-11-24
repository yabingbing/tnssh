## 目的
這份檔案提供給 AI 編碼助理（Copilot / agents）一份精簡、可執行的導覽，讓你能快速在此專案中進行修改、除錯與擴充。

## 專案大致架構（big picture）
- `main.py`：啟動入口。建立 `commands.Bot`，載入多個 cog（在 `cogs/` 與 `Bing/` 下），並包含 `on_message` 的路由邏輯。
- `cogs/`：功能模組（Cog）集合，每個檔案通常會實作一個 Cog 類別並提供 `async def setup(bot)` 以便用 `bot.load_extension` 載入。
- `Bing/`：與 AI（Gemini）互動的實作（例如 `Bing1.py`）。包含 prompt、短期記憶 (`memory.json`) 與歷史 (`history.json`) 的本地儲存。
- 第三方整合：Google Sheets (`gspread` + service account 使用 `credentials.json`)、Google Generative AI (`google-generativeai`)、Discord (`discord.py`)、Selenium（webdriver）等。

## 關鍵開發/執行流程
- 安裝依賴：`pip install -r requirements.txt`。
- 啟動 bot（在開發機通常直接執行）：
```powershell
python main.py
```
- 必要環境變數（放在 `.env`）：
  - `DISCORD_TOKEN`、`GEMINI_API_KEY`、`sheet_id`、`project_id`、`private_key_id`、`private_key`、`client_email`、`client_id` 等。
  - 注意：`main.py` 會在啟動時以 env 值寫入 `credentials.json`（private_key 需要包含 `\\n` 轉換）。

## 專案慣例與重要細節（只列出可發現的模式）
- Cog 結構：檔案內通常有一個 Cog 類別（有時名稱為 `Main`、`GeminiChat` 等），並提供 `async def setup(bot)` 以呼叫 `await bot.add_cog(...)`。
  - 範例：`cogs/greeting.py` 的 `Main` 類別 + `async def setup(bot)`。
- 訊息分流：`main.py` 的 `on_message` 先檢查是否為 AI 相關（會呼叫 `Bing` cog 的 `handle_message`），再檢查問候語 cog，最後才呼叫 `bot.process_commands`。
- Gemini / 記憶：`Bing/Bing1.py` 使用 `Bing/prompt.txt`、`Bing/memory.json`、`Bing/history.json`，並有 `safe_send` 分段發訊息的邏輯（注意 Discord 2000 字限制，實作上用 1900 截斷）。

## 要注意的現有實作陷阱（可直接被 agent 發現）
- `main.write_credentials_json()` 會以 env 生成 `credentials.json` 並做 `private_key.replace("\\\\n","\\n")`，確保 `.env` 中 private_key 的格式可經此轉換。
- 在 `main.write_credentials_json()` 中，`client_email` 與 `CLIENT_EMAIL` 的大小寫不一致（`client_email` 用於字典欄位，但 `client_x509_cert_url` 使用 `os.getenv('CLIENT_EMAIL')`）——部署時請確認 `.env` 同時含兩者或修正大小寫一致性。

## 修改/擴充建議（如何安全變更）
- 新增 Cog：在 `cogs/` 下建立新檔案，實作 Cog 類別並提供 `async def setup(bot)`；在 `main.py` 的 `main()` 中加入 `await bot.load_extension('cogs.your_cog')` 測試之。
- 變更 AI prompt 或模型：`Bing/prompt.txt` 與 `Bing/Bing1.py` 的 `model` 設定是關鍵點，先在測試頻道（或 DM）做小流量測試再推到正式頻道。
- Google Sheet 權限：`cogs/greeting.py` 使用 `gspread` 與 `credentials.json`，若無法連線請先檢查 `credentials.json`（由 `main.py` 產生）與 `sheet_id` 是否正確。

## 快速示例（常見任務）
- 新增一個 reply 指令：在 `cogs/` 新增檔案，示範 Cog 模板請參照 `cogs/greeting.py`。
- 清除 Gemini 記憶：`b!forget` 指令會在 `Bing1.py` 中清空 `Bing/memory.json`。

## 檔案參考（撰寫指引時常引用）
- 啟動與路由：`main.py`
- Greeting 示例：`cogs/greeting.py`
- AI / Gemini：`Bing/Bing1.py`, `Bing/prompt.txt`, `Bing/memory.json`, `Bing/history.json`
- 依賴清單：`requirements.txt`

## 若不清楚請詢問
- 我已讀取 `README.md`, `main.py`, `cogs/greeting.py`, `Bing/Bing1.py` 與 `requirements.txt`。如果你想要我將風險/改動點轉成 PR 草稿或自動化測試範例（例如對 `Bing` 的 mock 測試），告訴我要模擬哪個場景。

---
請審閱這個版本：若需要補充更多實例（例如新增 Cog 的最小可運作範例或 `.env` 的完整範例），回覆我需要的細節，我會再迭代。 
