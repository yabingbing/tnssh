import discord
from discord.ext import commands
import google.generativeai as genai
import json
import os
from datetime import datetime
import dotenv
dotenv.load_dotenv()  # 從 .env 檔案讀取環境變數
GEMINI_API_KEY = os.getenv("gemini_api_key")  # 從環境變數讀取 Gemini API 金鑰

MEMORY_FILE = "Bing/memory.json"
PROMPT_FILE = "Bing/prompt.txt"
HISTORY_FILE = "Bing/history.json"

class Bing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prompt = self.load_prompt()

        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        os.makedirs("Bing", exist_ok=True)
       

        if not os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'w') as f:
                json.dump({}, f)

    def load_prompt(self):
        if os.path.exists(PROMPT_FILE):
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []

    def load_memory(self):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)

    def save_memory(self, memory):
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=2)

    def save_history(self, history):
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)

    async def handle_message(self, message: discord.Message):
        if message.author.bot:
            return
        print(f"✅ Gemini 收到訊息：{message.content} 來自 {message.author}")

        if self.bot.user in message.mentions or message.reference:
            memory = self.load_memory()
            user_id = str(message.author.id)
            user_history = memory.get(user_id, [])
            user_history.append(message.content)

            prompt = self.load_prompt()
            history = self.load_history()

            # Gemini input
            content = [
                {"role": "system", "parts": [prompt]},
                *history,
                {"role": "user", "parts": [message.content]}
            ]

            response = await self.model.generate_content(content)
            print("AI 回應內容:", response.text)

            reply = response.text
            await message.reply(reply)

            # 更新記憶
            user_history.append(reply)
            memory[user_id] = user_history
            self.save_memory(memory)

            # 加入長期 history
            history.append({"role": "user", "parts": [message.content]})
            history.append({"role": "model", "parts": [reply]})
            self.save_history(history)

    @commands.command(name="forget")
    async def forget(self, ctx):
        memory = self.load_memory()
        user_id = str(ctx.author.id)
        if user_id in memory:
            del memory[user_id]
            self.save_memory(memory)
            await ctx.send(f"我忘記你剛剛說的話了啦～")
        else:
            await ctx.send("我沒記住你什麼東西欸。")

   
     
     
    

async def setup(bot):
    await bot.add_cog(Bing(bot))
    print("✅ GeminiChat cog has been loaded successfully!")


