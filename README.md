# tnssh
這是一個我自己做的機器人
然後主要是我們二中在用的
但有cog是附加功能 有興趣可以參考

## 使用 Docker 執行

先依照 `.env.example` 建立 `.env`，填入 Discord、Gemini、Pollinations 與 Google Sheets 需要的環境變數。

```bash
docker build -t tnssh-bot .
docker run --env-file .env --name tnssh-bot tnssh-bot
```

如果要背景執行：

```bash
docker run -d --env-file .env --restart unless-stopped --name tnssh-bot tnssh-bot
```

## 不使用 `.env` 做本地測試

這組測試不會使用 Discord、Gemini、Google Sheets 或外部圖片 API，只檢查可離線驗證的啟動與 helper 邏輯。

```bash
docker build -t tnssh-bot .
docker run --rm tnssh-bot python -m unittest discover -s tests
```

若要連線學校網站實測公告爬蟲：

```bash
docker run --rm -e RUN_LIVE_CRAWLER_TEST=1 tnssh-bot python -m unittest discover -s tests
```

## Debian系相容系統測試腳本

第一次在未執行過此腳本的系統上執行時，可使用此指令一併安裝 Chromium、chromedriver 與 Python 系統套件：

```bash
scripts/test_debian.sh --install-system-deps
```

在 Debian 或相容系統上，可以用腳本建立虛擬環境、安裝 Python 依賴並執行離線測試：

```bash
scripts/test_debian.sh
```

若要啟用會連線學校網站的爬蟲測試：

```bash
scripts/test_debian.sh --live-crawler
```