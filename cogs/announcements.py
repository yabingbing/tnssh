import discord
from discord.ext import commands, tasks
from datetime import datetime, time
from text import fetch_announcement  # 確保這個模組存在於專案根目錄
from dotenv import load_dotenv
import os
load_dotenv()
channel_id1 = os.getenv("CHANNEL_ID")  # 請在 .env 檔案中設定 CHANNEL_ID

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
        channel_id = channel_id1     # 替換成你的頻道 ID
        channel = self.bot.get_channel(channel_id)
        if channel:
            announcements = fetch_announcement()
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
        announcements = fetch_announcement()
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