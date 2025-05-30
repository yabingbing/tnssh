import asyncio
import discord
from discord.ext import commands
from Bing.call_gemini import call_gemini


class SummaryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='sum')
    async def summarize_messages(self, ctx, limit: int = 100):
      
        """統整指定數量內的訊息"""
        if limit > 500:
            await ctx.send("最多只能看 500 則訊息啦！")
            return

        messages = []
        async for message in ctx.channel.history(limit=limit):
            if not message.author.bot:
                messages.append(f"{message.author.name}: {message.content}")

        prompt = "用你主觀的角度統整評價這些話題語句 並且您的回覆不能超過200字： \n\n"
        prompt += "\n".join(reversed(messages))  # 由舊到新

        
        

        # 呼叫 Gemini API
        try:
             
            async with ctx.typing():
             summary = call_gemini(prompt)
             await asyncio.sleep(5)
            print (f"{summary}")
            await ctx.send(f"**以下是你要的統整：**\n{summary}")

        except Exception as e:
            await ctx.send(f"哎呀，出錯啦：{e}")

async def setup(bot):
    await bot.add_cog(SummaryCog(bot))
    print("✅ Summary cog has been loaded successfully!")
