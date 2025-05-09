# 1. 使用 Python 的官方映像檔
FROM python:3.12-slim

# 2. 設定工作目錄
WORKDIR /app

# 3. 安裝必要工具（例如 Chromium）
RUN apt update && apt install -y \
    wget \
    unzip \
    chromium \
    chromium-driver \
    && apt clean

# 4. 複製專案檔案到容器中
COPY . .

# 5. 給 chromedriver 執行權限（你也可以直接用 Linux 版就不用 copy .exe）
RUN chmod +x ./drivers/chromedriver


# 6. 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 7. 設定環境變數，讓 selenium 找到 Chrome
ENV PATH="/usr/lib/chromium:${PATH}"
ENV CHROME_BIN="/usr/bin/chromium"
ENV CHROMEDRIVER_PATH="/usr/bin/chromedriver"

# 8. 執行你的 bot
CMD ["python", "discord_bot.py"]
