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
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="b!", intents=intents)

def build_credentials_dict():
    required_keys = [
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
    ]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        return None, missing_keys

    client_email = os.getenv("client_email")
    return {
        "type": "service_account",
        "project_id": os.getenv("project_id"),
        "private_key_id": os.getenv("private_key_id"),
        "private_key": os.getenv("private_key").replace("\\n", "\n"),
        "client_email": client_email,
        "client_id": os.getenv("client_id"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
        "universe_domain": "googleapis.com"
    }, []

def write_credentials_json():
    credentials_dict, missing_keys = build_credentials_dict()
    if missing_keys:
        print(f"⚠️ 未建立 credentials.json，缺少環境變數：{', '.join(missing_keys)}")
        return False

    with open("credentials.json", "w", encoding="utf-8") as f:
        json.dump(credentials_dict, f, ensure_ascii=False, indent=2)
    return True

# 啟動前產生 Google service account 憑證檔。
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

    # 取得問候語 Cog，若未載入則略過。
    greeting_cog = bot.get_cog("Main")

    # 問候語訊息交給 greeting Cog 處理。
    if greeting_cog and greeting_cog.get_greeting_type(message.content):
        await greeting_cog.handle_message(message)
        return # 已處理問候語，不再交給其他指令流程。

    await bot.process_commands(message)


async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("缺少 DISCORD_TOKEN 環境變數，無法啟動 Discord bot")

    await bot.load_extension("cogs.announcements")
 #   await bot.load_extension("cogs.greeting")  # 需要問候語功能時再載入。
#    await bot.load_extension("cogs.answer_book")  # 需要答案之書功能時再載入。
    await bot.load_extension("cogs.sum")  # 載入訊息摘要功能。
    await bot.load_extension("cogs.recipes")  # 載入食譜抽選功能。
    await bot.load_extension("cogs.andy")  # 載入圖片語錄功能。
    await bot.load_extension("Bing.Bing1")  # 載入 Gemini 對話功能。
    await bot.load_extension("cogs.repeat_detector")
    await bot.load_extension("Bing.image")  # 載入圖片生成指令。
    await bot.load_extension("Bing.video")  # 載入影片生成指令。
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
