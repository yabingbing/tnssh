import discord
from discord.ext import commands
import google.generativeai as genai
import json
import os
import dotenv

dotenv.load_dotenv()
GEMINI_API_KEY = os.getenv("gemini_api_key")

MEMORY_FILE = "Bing/memory.json"
PROMPT_FILE = "Bing/prompt.txt"
HISTORY_FILE = "Bing/history.json"

class Bing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prompt = self.load_prompt() 

       
        try:
            with open("Bing/filtered_messages.txt", 'r', encoding='utf-8') as f:
                filtered_messages = f.read()
        except FileNotFoundError:
            filtered_messages = "You are a helpful assistant."  # 預設提示以防萬一

        # 把讀到的內容加到 prompt 裡
        self.prompt += "\n以下是語句範例：\n"  + filtered_messages

        # --- 修正點 1: 設定 API 金鑰並初始化模型 ---
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # 使用正確的模型名稱，並傳入系統提示
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash", 
                system_instruction=self.prompt
            )
            print("✅ Gemini Model (gemini-1.5-flash) loaded successfully with system prompt.")
        except Exception as e:
            print(f"❌ Failed to configure Gemini Model: {e}")
            self.model = None

        os.makedirs("Bing", exist_ok=True)
        if not os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'w') as f:
                json.dump({}, f)

    def load_prompt(self):
        if os.path.exists(PROMPT_FILE):
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        return "You are a helpful assistant." # 提供一個預設提示以防萬一

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def save_history(self, history):
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)

    # 記憶功能 (memory) 保持不變
    def load_memory(self):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)

    def save_memory(self, memory):
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=2)

    async def handle_message(self, message: discord.Message):
        if message.author.bot or not self.model:
            return
        
        print(f"✅ Gemini received message: '{message.content}' from {message.author}")

        # 觸發條件不變：提及(mention)或回覆(reference)
        if self.bot.user in message.mentions or message.reference:
            
            # 顯示 "正在輸入..." 提示，讓使用者知道機器人有在處理
            async with message.channel.typing():
                try:
                    history = self.load_history()
                    memory = self.load_memory()

                    # --- 修正點 2: 移除 content 中的 system role ---
                    # 系統提示已經在初始化時提供給模型了
                    content = [
                        *history,
                        *memory,
                        {"role": "user", "parts": [message.content]}
                    ]

                    response = await self.model.generate_content_async(content)
                    reply = response.text
                    
                    print("AI Response:", reply)
                    await message.reply(reply)

                    # 更新長期 history
                    memory.append({"role": "user", "parts": [message.content]})
                    memory.append({"role": "model", "parts": [reply]})
                    self.save_memory(memory)

                    # 更新短期 history
                    (memory)

                # --- 修正點 3: 增加錯誤處理 ---
                except Exception as e:
                    print(f"❌ An error occurred while generating content: {e}")
                    await message.reply("抱歉，我在思考的時候好像撞到頭了，請再試一次。")

    @commands.command(name="forget")
    async def forget(self, ctx):
        # 為了簡潔，這裡省略 forget 指令的程式碼，請保留你原本的即可
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
    # 這裡的 print 訊息可以不用改
    print("✅ GeminiChat cog has been loaded successfully!")