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
from urllib.parse import quote

load_dotenv()
POLLINATIONS_KEY = os.getenv("POLLINATIONS_KEY") or os.getenv("pollinations_key")

def build_pollinations_video_url(prompt: str) -> str:
    return f"https://gen.pollinations.ai/image/{quote(prompt, safe='')}"

def build_pollinations_headers(api_key: str = None) -> dict:
    headers = {"Accept": "*/*"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers

class VideoGenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 限制同時處理數量，避免影片生成請求互相阻塞。
        self.max_concurrent_tasks = 1
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        self.waiting_count = 0

    @app_commands.command(name="生成影片", description="輸入提示詞生成影片 (使用 Grok Video)")
    @app_commands.rename(translate_prompt="翻譯提示詞")  # 設定 Discord 指令參數顯示名稱。
    @app_commands.describe(prompt="輸入想要生成的影片內容", translate_prompt="是否由 AI 翻譯成英文 (預設: 否)")
    async def generate_video(
        self, 
        interaction: discord.Interaction, 
        prompt: str, 
        translate_prompt: bool = False # 預設不翻譯提示詞。
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

                # 準備實際送往影片生成 API 的提示詞。
                final_prompt = prompt  # 預設使用原始提示詞。
                
                if translate_prompt:
                    try:
                        instruction = f"請將以下文字完整翻譯成英文，不要改意思，只翻譯文字，不要加多餘說明:\n{prompt}"
                        translated_text = await asyncio.to_thread(call_gemini, instruction)
                        translated_text = translated_text.strip()
                        final_prompt = translated_text
                    except Exception as e:
                        print(f"翻譯失敗: {e}")
                        await interaction.followup.send(f" 翻譯服務暫時無法使用，將使用原始提示詞生成。", ephemeral=True)
                        final_prompt = prompt
                # 使用 final_prompt 呼叫 Pollinations 影片生成 API。
                url = build_pollinations_video_url(final_prompt)
                
                headers = build_pollinations_headers(POLLINATIONS_KEY)
                
                params = {
                    "model": "grok-video",
                    "seed": random.randint(0, 99999),
                    "enhance": "false"
                }

                # requests 是同步函式，放到執行緒避免卡住 bot。
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    # 影片生成較慢，保留較長 timeout。
                    lambda: requests.get(url, headers=headers, params=params, timeout=300) 
                )

                if response.status_code == 200:
                    video_data = io.BytesIO(response.content)
                    discord_file = discord.File(fp=video_data, filename="result.mp4")
                    
                    # 建立回傳給 Discord 的結果訊息。
                    msg_content = f" **影片生成完畢！**\n**提示詞:** {prompt}"
                    
                    # 有翻譯時一併顯示實際使用的提示詞。
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
                # 若狀態訊息尚未建立，改用 followup 回報錯誤。
                if status_message:
                    await status_message.edit(content=f"發生錯誤：{str(e)}")
                else:
                    await interaction.followup.send(f"發生錯誤：{str(e)}")
            
            finally:
                self.waiting_count -= 1

# Discord 載入此 Cog 時會呼叫 setup。
async def setup(bot):
    await bot.add_cog(VideoGenCog(bot))
