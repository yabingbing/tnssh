import discord
from discord.ext import commands
import random
import asyncio
import google.generativeai as genai
from collections import deque
import os
import json
from dotenv import load_dotenv

# 載入 .env
load_dotenv()

# 從環境變數拿 Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 初始化 Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

MEMORY_FILE = "Bing/memory.json"

class GeminiReplyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_buffer = deque(maxlen=10)  # 記錄最近訊息

        # 確保記憶檔案存在
        os.makedirs("Bing", exist_ok=True)
        if not os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'w', encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def load_memory(self):
        with open(MEMORY_FILE, 'r', encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_memory(self, memory):
        with open(MEMORY_FILE, 'w', encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        # 存最近訊息
        self.message_buffer.append(f"{message.author.display_name}: {message.content}")

        # 丟骰子決定觸發 (1/10)
        if random.randint(1, 50) == 1:
            await self.try_gemini_reply(message)

    async def try_gemini_reply(self, message: discord.Message):
        try:
            context = "\n".join(self.message_buffer)
            response = model.generate_content(
                f"這是一個 Discord 群組的對話紀錄，請用20字以內輕鬆幽默的方式貼合話題回覆：\n{context}"
            )

            reply_text = response.text.strip()
            if reply_text:
                # 用 reply 回覆觸發的訊息
                await message.reply(reply_text[:1900])

                # ✅ 把這次對話存進短期記憶
                memory = self.load_memory()
                memory.append({"role": "user", "parts": [message.content]})
                memory.append({"role": "model", "parts": [reply_text]})
                self.save_memory(memory)

        except Exception as e:
            print(f"Gemini error: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(GeminiReplyCog(bot))
    print("✅ GeminiReplyCog has been loaded successfully!")
