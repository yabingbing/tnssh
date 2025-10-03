import discord
from discord.ext import commands
import random
import google.generativeai as genai
import json
import os
from collections import deque
from dotenv import load_dotenv

# 載入 .env
load_dotenv()

# 從環境變數拿 Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 記憶檔案
MEMORY_FILE = "Bing/memory.json"
PROMPT_FILE = "Bing/prompt.txt"
HISTORY_FILE = "Bing/history.json"

class GeminiChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_buffer = deque(maxlen=10)  # 短期對話緩衝
        self.prompt = self.load_prompt()

        # 嘗試讀取範例訊息
        try:
            with open("Bing/filtered_messages.txt", 'r', encoding='utf-8') as f:
                filtered_messages = f.read()
        except FileNotFoundError:
            filtered_messages = "You are a helpful assistant."

        self.prompt += "\n以下是語句範例：\n" + filtered_messages

        # 初始化 Gemini
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=self.prompt
            )
            print("✅ Gemini Model (gemini-2.5-flash) loaded successfully with system prompt.")
        except Exception as e:
            print(f"❌ Failed to configure Gemini Model: {e}")
            self.model = None

        # 確保檔案存在
        os.makedirs("Bing", exist_ok=True)
        for file in [MEMORY_FILE, HISTORY_FILE]:
            if not os.path.exists(file):
                with open(file, 'w', encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)

    # ------------------ 檔案存取 ------------------
    def load_prompt(self):
        if os.path.exists(PROMPT_FILE):
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        return "You are a helpful assistant."

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def save_history(self, history):
        with open(HISTORY_FILE, 'w', encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def load_memory(self):
        with open(MEMORY_FILE, 'r', encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_memory(self, memory):
        with open(MEMORY_FILE, 'w', encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

    # ------------------ 自動回覆 ------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # 加入短期訊息緩衝
        self.message_buffer.append(f"{message.author.display_name}: {message.content}")

        # 觸發條件 1: 隨機骰子 (1/10)
        if random.randint(1, 100) == 1:
            await self.try_autoreply(message)

        # 觸發條件 2: @bot 或 回覆 bot
        if self.bot.user in message.mentions or message.reference:
            await self.try_chat_reply(message)

    async def try_autoreply(self, message: discord.Message):
        try:
            context = "\n".join(self.message_buffer)
            response = self.model.generate_content(
                f"這是一個 Discord 群組的對話紀錄，請用20字以內輕鬆幽默的方式貼合話題回覆：\n{context}"
            )
            reply_text = response.text.strip()

            if reply_text:
                await message.reply(reply_text[:1900])

                # 存進短期記憶
                memory = self.load_memory()
                memory.append({"role": "user", "parts": [message.content]})
                memory.append({"role": "model", "parts": [reply_text]})
                self.save_memory(memory)

        except Exception as e:
            print(f"❌ AutoReply error: {e}")

    async def try_chat_reply(self, message: discord.Message):
        try:
            async with message.channel.typing():
                history = self.load_history()
                memory = self.load_memory()

                content = [
                    *history,
                    *memory,
                    {"role": "user", "parts": [message.content]}
                ]

                response = await self.model.generate_content_async(content)
                reply = response.text

                await message.reply(reply)

                # 存進短期記憶
                memory.append({"role": "user", "parts": [message.content]})
                memory.append({"role": "model", "parts": [reply]})
                self.save_memory(memory)

        except Exception as e:
            print(f"❌ ChatReply error: {e}")
            await message.reply("抱歉，我剛剛腦袋打結了，請再說一次！")

    # ------------------ 指令 ------------------
    @commands.command(name="forget")
    async def forget(self, ctx):
        """清除群組的對話記憶"""
        self.save_memory([])
        await ctx.send("好啦，我把所有對話都忘掉了 😵‍💫")

# ------------------ 啟動 ------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(GeminiChat(bot))
    print("✅ GeminiChat cog has been loaded successfully!")
