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

async def main():
    await bot.load_extension("cogs.announcements")
    await bot.load_extension("cogs.greeting")  # 如 greeting cog 存在則一起載入
    await bot.start(DISCORD_TOKEN)

asyncio.run(main())