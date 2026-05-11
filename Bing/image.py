import discord
from discord import app_commands
from discord.ext import commands
import requests
from Bing.call_gemini import call_gemini
import io
import asyncio
from dotenv import load_dotenv
import os
from urllib.parse import quote

load_dotenv()
POLLINATIONS_KEY = os.getenv("POLLINATIONS_KEY") or os.getenv("pollinations_key")

def build_pollinations_image_url(prompt: str) -> str:
    return f"https://gen.pollinations.ai/image/{quote(prompt, safe='')}"

def build_pollinations_headers(api_key: str = None) -> dict:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers

class ImageGenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 限制同時處理數量，避免生成 API 被大量請求塞滿。
        self.max_concurrent_tasks = 1
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        self.waiting_count = 0

    @app_commands.command(name="生成圖片", description="輸入提示詞生成圖片")
    @app_commands.rename(translate_prompt="翻譯提示詞")  # 設定 Discord 指令參數顯示名稱。
    @app_commands.describe(prompt="輸入想要生成的圖片內容", translate_prompt="是否由 AI 翻譯成英文 (預設: 否)")
    async def generate_image(
        self, 
        interaction: discord.Interaction, 
        prompt: str, 
        translate_prompt: bool = False  # 預設不翻譯提示詞。
    ):
        await interaction.response.defer()

        self.waiting_count += 1
        queue_number = self.waiting_count - self.max_concurrent_tasks
        
        status_message = None
        if queue_number > 0:
            status_message = await interaction.followup.send(
                f"繪圖請求已受理！目前伺服器繁忙，您前面還有 **{queue_number}** 人，請耐心等候..."
            )
        else:
            status_message = await interaction.followup.send(f"在畫了:D")

        async with self.semaphore:
            try:
                if queue_number > 0:
                    await status_message.edit(content="輪到您了！正在開始繪製圖片...")

                # 準備實際送往圖片生成 API 的提示詞。
                final_prompt = prompt  # 預設使用原始輸入。
                
                # 使用者要求翻譯時，先用 Gemini 轉成英文。
                if translate_prompt:
                    try:
                        instruction = f"請將以下文字完整翻譯成英文，不要改意思，只翻譯文字，不要加多餘說明:\n{prompt}"
                        # 翻譯可能阻塞，因此放到背景執行緒。
                        translated_text = await asyncio.to_thread(call_gemini, instruction)
                        translated_text = translated_text.strip()
                        final_prompt = translated_text # 使用翻譯後提示詞生成圖片。
                    except Exception as e:
                        # 翻譯失敗時改用原始提示詞，讓生成流程仍可繼續。
                        print(f"翻譯失敗: {e}")
                        await interaction.followup.send(f"⚠️ 翻譯服務暫時無法使用，將使用原始提示詞生成。", ephemeral=True)
                        final_prompt = prompt

                # 使用 final_prompt 呼叫 Pollinations 圖片生成 API。
                url = build_pollinations_image_url(final_prompt)
                headers = build_pollinations_headers(POLLINATIONS_KEY)
                params = {
                    "model": "gptimage", "width": 1024, "height": 1024,
                    "seed": 0, "enhance": "false", "negative_prompt": "blurry",
                    "safe": "false", "quality": "medium"
                }

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: requests.get(url, headers=headers, params=params, timeout=40)
                )

                if response.status_code == 200:
                    image_data = io.BytesIO(response.content)
                    discord_file = discord.File(fp=image_data, filename="result.png")
                    
                    # 建立回傳給 Discord 的結果訊息。
                    msg_content = f"✨ **生成完畢！**\n**提示詞:** {prompt}"
                    
                    # 有翻譯時一併顯示實際使用的提示詞。
                    if translate_prompt:
                        msg_content += f"\n**翻譯提示詞:** {final_prompt}"
                    
                    await status_message.edit(content=msg_content, attachments=[discord_file])
                else:
                    await status_message.edit(content=f"❌ 圖片生成失敗，API 狀態碼：{response.status_code}")

            except Exception as e:
                if status_message:
                    await status_message.edit(content=f"發生錯誤：{str(e)}")
                else:
                    await interaction.followup.send(f"發生錯誤：{str(e)}")
            
            finally:
                self.waiting_count -= 1

async def setup(bot):
    await bot.add_cog(ImageGenCog(bot))
