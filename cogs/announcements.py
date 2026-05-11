import discord
from discord.ext import commands, tasks
from datetime import datetime, time
from text import fetch_announcement  # 從根目錄的爬蟲模組取得公告資料
from dotenv import load_dotenv
import os
import asyncio
load_dotenv()
channel_id1 = os.getenv("CHANNEL_ID")  # 從環境變數讀取公告頻道 ID

def parse_channel_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fetch_announcements.start()

    def cog_unload(self):
        self.fetch_announcements.cancel()

    @tasks.loop(minutes=1)
    async def fetch_announcements(self):
        now = datetime.now()
        target_time = time(17, 0)
        if now.time().hour == target_time.hour and now.time().minute == target_time.minute:
            print("現在是 17:00，開始爬蟲")
            await self.fetch_and_send_announcements()

    async def fetch_and_send_announcements(self):
        channel_id = parse_channel_id(channel_id1)
        if channel_id is None:
            print("❌ CHANNEL_ID 未設定或不是有效數字，無法發送公告。")
            return

        channel = self.bot.get_channel(channel_id)
        if channel:
            announcements = await asyncio.to_thread(fetch_announcement)
            if announcements:
                announcement_list = announcements.split("\n\n")
                for announcement in announcement_list:
                    if len(announcement) > 2000:
                        chunks = [announcement[i:i+2000] for i in range(0, len(announcement), 2000)]
                        for chunk in chunks:
                            await channel.send(chunk)
                    else:
                        await channel.send(announcement)
            else:
                print("沒有公告可發送。")

    @commands.command()
    async def get_announcements(self, ctx):
        announcements = await asyncio.to_thread(fetch_announcement)
        if announcements:
            announcement_list = announcements.split("\n\n")
            for announcement in announcement_list:
                if len(announcement) > 2000:
                    chunks = [announcement[i:i+2000] for i in range(0, len(announcement), 2000)]
                    for chunk in chunks:
                        await ctx.send(chunk)
                else:
                    await ctx.send(announcement)
        else:
            await ctx.send("目前沒有公告可以發送。")
            print("沒有公告，不發送訊息。")

async def setup(bot):
    await bot.add_cog(Announcements(bot))
