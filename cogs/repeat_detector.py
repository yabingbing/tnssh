import discord
from discord.ext import commands

class RepeatDetector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 以頻道為單位記錄上一則訊息與連續次數。
        self.cache = {}

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        # 避免機器人回覆觸發自己的監聽器。
        if msg.author.bot:
            return

        channel_id = msg.channel.id
        content = msg.content.strip()

        # 第一次看到此頻道時建立紀錄。
        if channel_id not in self.cache:
            self.cache[channel_id] = {"last_msg": content, "count": 1}
            return

        last_msg = self.cache[channel_id]["last_msg"]

        # 相同訊息累計次數，不同則重新計算。
        if content == last_msg:
            self.cache[channel_id]["count"] += 1
        else:
            # 訊息內容不同時重置頻道狀態。
            self.cache[channel_id] = {"last_msg": content, "count": 1}
            return

        # 達到門檻時提醒使用者。
        if self.cache[channel_id]["count"] == 4:
            await msg.channel.send(f"為什麼要一直說{content}")
            # 重置計數，避免同一句話持續觸發。
            self.cache[channel_id]["count"] = 0

async def setup(bot):
    await bot.add_cog(RepeatDetector(bot))
