from datetime import datetime, time
import discord
from discord.ext import tasks, commands
from text import fetch_announcement  # 導入爬蟲模塊
import os
from dotenv import load_dotenv

# 加載 .env 文件
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")



intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"登入成功，當前機器人為: {bot.user.name}")
    # 啟動定時任務
    fetch_announcements.start()

# 定義定時任務，每分鐘檢查一次
@tasks.loop(minutes=1)
async def fetch_announcements():
    """檢查當前時間是否為目標時間，並執行爬取"""
    now = datetime.now()
    target_time = time(17, 00)  # 目標時間：每天 17:00

    if now.time().hour == target_time.hour and now.time().minute == target_time.minute:
        print("現在是 17:00 開始爬蟲")
        await fetch_and_send_announcements()

async def fetch_and_send_announcements():
    channel_id = 1279494493065838724  # 替換成你自己的 Discord 頻道 ID
    channel = bot.get_channel(channel_id)
    
    if channel:
        announcements = fetch_announcement()  # 取得爬蟲抓取的公告
        if announcements:
            # 分割公告為多段，並處理長度限制
            announcement_list = announcements.split("\n\n")
            for announcement in announcement_list:
                if len(announcement) > 2000:
                    # 將超過 2000 字元的公告分段發送
                    chunks = [announcement[i:i+2000] for i in range(0, len(announcement), 2000)]
                    for chunk in chunks:
                        await channel.send(chunk)
                else:
                    await channel.send(announcement)
        else:
            print("沒有公告可發送。")

@bot.command()
async def get_announcements(ctx):
    """手動觸發爬蟲抓取公告並發送"""
    announcements = fetch_announcement()
    if announcements:
        # 分割公告為多段，並處理長度限制
        announcement_list = announcements.split("\n\n")
        for announcement in announcement_list:
            if len(announcement) > 2000:
                # 將超過 2000 字元的公告分段發送
                chunks = [announcement[i:i+2000] for i in range(0, len(announcement), 2000)]
                for chunk in chunks:
                    await ctx.send(chunk)
            else:
                await ctx.send(announcement)
    else:
        await ctx.send("目前沒有公告可以發送。")
        print("沒有公告，不發送訊息。")

# 啟動機器人
bot.run(DISCORD_TOKEN)  # 請替換為你的 Discord Bot Token


