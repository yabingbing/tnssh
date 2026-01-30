import discord
from discord.ext import commands

class RepeatDetector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {channel_id: {"last_msg": str, "count": int}}
        self.cache = {}

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        # 忽略機器人自己的訊息
        if msg.author.bot:
            return

        channel_id = msg.channel.id
        content = msg.content.strip()

        # 初始化
        if channel_id not in self.cache:
            self.cache[channel_id] = {"last_msg": content, "count": 1}
            return

        last_msg = self.cache[channel_id]["last_msg"]

        # 如果跟上一則訊息一樣
        if content == last_msg:
            self.cache[channel_id]["count"] += 1
        else:
            # 不同訊息 → 重置
            self.cache[channel_id] = {"last_msg": content, "count": 1}
            return

        # 如果連續三次
        if self.cache[channel_id]["count"] == 4:
            await msg.channel.send(f"為什麼要一直說{content}")
            # 重置避免無限循環
            self.cache[channel_id]["count"] = 0

async def setup(bot):
    await bot.add_cog(RepeatDetector(bot))
