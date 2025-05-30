import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
    try:
        synced = await bot.tree.sync()
        print(f"✅ 同步了 {len(synced)} 個應用指令")
    except Exception as e:
        print(f"❌ 同步指令失敗：{e}")

async def main():
    await bot.load_extension("cogs.announcements")
    await bot.load_extension("cogs.greeting")  # 如 greeting cog 存在則一起載入
    await bot.load_extension("cogs.answer_book")  # 如 answer_book cog 存在則一起載入
    await bot.load_extension("cogs.sum")  # 如 sum cog 存在則一起載入
    await bot.load_extension("cogs.recipes")  # 如 recipes cog 存在則一起載入
    await bot.start(DISCORD_TOKEN)

asyncio.run(main())