import discord
from discord import app_commands
from discord.ext import commands
import requests
from Bing.call_gemini import call_gemini
import io
import asyncio
from dotenv import load_dotenv
import os
import random

load_dotenv()
POLLINATIONS_KEY = os.getenv("pollinations_key")

class VideoGenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 設定同時處理的最大人數
        self.max_concurrent_tasks = 1
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        self.waiting_count = 0

    @app_commands.command(name="生成影片", description="輸入提示詞生成影片 (使用 Grok Video)")
    @app_commands.rename(translate_prompt="翻譯提示詞")  # Discord UI 顯示名稱
    @app_commands.describe(prompt="輸入想要生成的影片內容", translate_prompt="是否由 AI 翻譯成英文 (預設: 否)")
    async def generate_video(
        self, 
        interaction: discord.Interaction, 
        prompt: str, 
        translate_prompt: bool = False # 默認否
    ):
        await interaction.response.defer()

        self.waiting_count += 1
        queue_number = self.waiting_count - self.max_concurrent_tasks
        
        status_message = None
        if queue_number > 0:
            status_message = await interaction.followup.send(
                f"🎬 影片請求已受理！目前伺服器繁忙，您前面還有 **{queue_number}** 人，請耐心等候..."
            )
        else:
            status_message = await interaction.followup.send(f" 正在生成影片中，請稍候...")

        async with self.semaphore:
            try:
                if queue_number > 0:
                    await status_message.edit(content=" 輪到您了！正在開始製作影片...")

                # --- 翻譯邏輯 (同圖片生成) ---
                final_prompt = prompt  # 預設使用原始提示詞
                
                if translate_prompt:
                    try:
                        instruction = f"請將以下文字完整翻譯成英文，不要改意思，只翻譯文字，不要加多餘說明:\n{prompt}"
                        translated_text = call_gemini(instruction).strip()
                        final_prompt = translated_text
                    except Exception as e:
                        print(f"翻譯失敗: {e}")
                        await interaction.followup.send(f" 翻譯服務暫時無法使用，將使用原始提示詞生成。", ephemeral=True)
                        final_prompt = prompt
                # ---------------------------

                # 2️⃣ 請求 API (使用 final_prompt)
                url = f"https://gen.pollinations.ai/image/{final_prompt}"
                
                headers = {
                    "Accept": "*/*",
                    "Authorization": f"Bearer {POLLINATIONS_KEY}" if POLLINATIONS_KEY else None
                }
                
                params = {
                    "model": "grok-video",
                    "seed": random.randint(0, 99999),
                    "enhance": "false"
                }

                # 使用 run_in_executor
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    # 影片生成較慢，Timeout 維持 120秒
                    lambda: requests.get(url, headers=headers, params=params, timeout=300) 
                )

                if response.status_code == 200:
                    video_data = io.BytesIO(response.content)
                    discord_file = discord.File(fp=video_data, filename="result.mp4")
                    
                    # 組合訊息
                    msg_content = f" **影片生成完畢！**\n**提示詞:** {prompt}"
                    
                    # 如果有開啟翻譯，顯示翻譯後的內容
                    if translate_prompt:
                        msg_content += f"\n**翻譯提示詞:** {final_prompt}"
                        
                    msg_content += "\n(Model: Grok-Video)"

                    await status_message.edit(
                        content=msg_content, 
                        attachments=[discord_file]
                    )
                else:
                    await status_message.edit(content=f" 影片生成失敗，API 狀態碼：{response.status_code}")

            except requests.Timeout:
                await status_message.edit(content=" 請求超時：影片生成花費太長時間，請稍後再試。")
            except Exception as e:
                # 這裡加個判斷，如果 status_message 還沒發送成功 (極端情況)，用 followup 發
                if status_message:
                    await status_message.edit(content=f"發生錯誤：{str(e)}")
                else:
                    await interaction.followup.send(f"發生錯誤：{str(e)}")
            
            finally:
                self.waiting_count -= 1

# 載入函數
async def setup(bot):
    await bot.add_cog(VideoGenCog(bot))