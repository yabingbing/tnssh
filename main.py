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
    await bot.start(DISCORD_TOKEN)

asyncio.run(main())