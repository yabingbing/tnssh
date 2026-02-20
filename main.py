import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from http.server import SimpleHTTPRequestHandler
import socketserver
import threading

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True 

bot = commands.Bot(command_prefix="b!", intents=intents)

def write_credentials_json():
    credentials_dict = {
        "type": "service_account",
        "project_id": os.getenv("project_id"),
        "private_key_id": os.getenv("private_key_id"),
        "private_key": os.getenv("private_key").replace("\\n", "\n"),
        "client_email": os.getenv("client_email"),
        "client_id": os.getenv("client_id"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('CLIENT_EMAIL')}",
        "universe_domain": "googleapis.com"
    }

    with open("credentials.json", "w", encoding="utf-8") as f:
        json.dump(credentials_dict, f, ensure_ascii=False, indent=2)

# 寫入檔案
write_credentials_json()

@bot.event
async def on_ready():
    print(f"✅ Bot 已上線：{bot.user.name}")
    print("🔍 已載入的 Cogs：", list(bot.cogs.keys()))
    try:
        synced = await bot.tree.sync()
        print(f"✅ 同步了 {len(synced)} 個應用指令")
    except Exception as e:
        print(f"❌ 同步指令失敗：{e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 取得 cogs
    bing_cog = bot.get_cog("Bing")
    greeting_cog = bot.get_cog("Main")

    # 優先處理 AI 提及或回覆
    # 檢查訊息是否提及機器人或是一個回覆
    if bing_cog:
    # 是否 @ 機器人
      mentioned_bot = bot.user in message.mentions

      # 是否回覆機器人的訊息
      replied_to_bot = False
      if message.reference:
        replied_message = await message.channel.fetch_message(message.reference.message_id)
        if replied_message.author.id == bot.user.id:
            replied_to_bot = True

      if mentioned_bot or replied_to_bot:
        await bing_cog.handle_message(message)
        return

    # 其次處理問候語
    # 檢查訊息是否包含問候語關鍵字
    if greeting_cog and greeting_cog.get_greeting_type(message.content):
        await greeting_cog.handle_message(message)
        return # 處理完畢，結束函式

    # 如果以上條件都不滿足，才檢查是否為指令 (例如 !forget)
    await bot.process_commands(message)


async def main():
    await bot.load_extension("cogs.announcements")
 #   await bot.load_extension("cogs.greeting")  # 如 greeting cog 存在則一起載入
#    await bot.load_extension("cogs.answer_book")  # 如 answer_book cog 存在則一起載入
    await bot.load_extension("cogs.sum")  # 如 sum cog 存在則一起載入
    await bot.load_extension("cogs.recipes")  # 如 recipes cog 存在則一起載入
    await bot.load_extension("cogs.andy")  # 如 andy cog 存在則一起載入
    await bot.load_extension("Bing.Bing1")  # 如 gemini_chat cog 存在則一起載入
    await bot.load_extension("cogs.repeat_detector")
    await bot.load_extension("Bing.image")  # 載入圖片生成 cog
    await bot.load_extension("Bing.video")  # 載入影片生成 cog
    await bot.start(DISCORD_TOKEN)



asyncio.run(main())