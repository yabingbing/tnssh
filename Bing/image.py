import discord
from discord import app_commands
from discord.ext import commands
import requests
from Bing.call_gemini import call_gemini
import io
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
POLLINATIONS_KEY = os.getenv("pollinations_key")

class ImageGenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 設定同時處理的最大人數 (例如同時只幫 1 個人畫圖)
        self.max_concurrent_tasks = 1
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        # 目前正在排隊或處理中的總人數
        self.waiting_count = 0

    @app_commands.command(name="生成圖片", description="輸入提示詞生成圖片")
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        # 增加排隊計數
        self.waiting_count += 1
        
        # 計算前方有多少人 (目前排隊數 - 最大處理數)
        queue_number = self.waiting_count - self.max_concurrent_tasks
        
        # 如果需要排隊，發送通知
        status_message = None
        if queue_number > 0:
            status_message = await interaction.followup.send(
                f"繪圖請求已受理！目前伺服器繁忙，您前面還有 **{queue_number}** 人，請耐心等候..."
            )
        else:
            status_message = await interaction.followup.send("在畫了:D")

        # 使用 Semaphore 進行排隊控制
        async with self.semaphore:
            try:
                # 如果排過隊，開始處理時更新一下訊息
                if queue_number > 0:
                    await status_message.edit(content="輪到您了！正在開始繪製圖片...")

                # 1️⃣ 翻譯
                instruction = f"請將以下文字完整翻譯成英文，不要改意思，只翻譯文字，不要加多餘說明:\n{prompt}"
                translated_prompt = call_gemini(instruction).strip()

                # 2️⃣ 請求 API
                url = f"https://gen.pollinations.ai/image/{translated_prompt}"
                headers = {"Authorization": f"Bearer {POLLINATIONS_KEY}"}
                params = {
                    "model": "gptimage", "width": 1024, "height": 1024,
                    "seed": 0, "enhance": "false", "negative_prompt": "blurry",
                    "safe": "false", "quality": "medium"
                }

                # 使用 run_in_executor 避免 requests 阻塞非同步循環
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: requests.get(url, headers=headers, params=params, timeout=40)
                )

                if response.status_code == 200:
                    image_data = io.BytesIO(response.content)
                    discord_file = discord.File(fp=image_data, filename="result.png")
                    
                    await status_message.edit(content=f"✨ **生成完畢！**\n**提示詞:** {prompt}", attachments=[discord_file])
                else:
                    await status_message.edit(content=f"❌ 圖片生成失敗，API 狀態碼：{response.status_code}")

            except Exception as e:
                await status_message.edit(content=f"發生錯誤：{str(e)}")
            
            finally:
                # 無論成功失敗，結束後都要減少計數
                self.waiting_count -= 1

# 載入函數
async def setup(bot):
    await bot.add_cog(ImageGenCog(bot))