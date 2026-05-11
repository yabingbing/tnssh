import discord
from discord.ext import commands
import os
import json
import io
import asyncio
from collections import deque
from dotenv import load_dotenv
from PIL import Image

# 使用新版 Google GenAI SDK。
from google import genai
from google.genai import types

# 載入本機環境變數。
load_dotenv()

# 從環境變數讀取 Gemini API 金鑰。
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 對話設定與記憶檔案路徑。
MEMORY_FILE = "Bing/memory.json"
PROMPT_FILE = "Bing/prompt.txt"
HISTORY_FILE = "Bing/history.json"

class GeminiChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_buffer = deque(maxlen=15)  # 保留最近訊息作為短期上下文。
        self.prompt = self.load_prompt()
        self.memory_lock = asyncio.Lock()
        self.max_memory_entries = 40

        # 初始化 Gemini 用戶端。
        try:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            # 預設文字對話模型。
            self.text_model_name = "gemini-2.5-flash" 
            # 圖片生成模型，可依需求替換為專用圖像模型。
            self.image_model_name = "gemini-2.5-flash" 
            
            print(f"✅ Gemini Client initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to configure Gemini Client: {e}")
            self.client = None

        # 確保記憶檔案存在，避免首次啟動讀取失敗。
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

    def load_memory(self):
        with open(MEMORY_FILE, 'r', encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_memory(self, memory):
        with open(MEMORY_FILE, 'w', encoding="utf-8") as f:
            json.dump(memory[-self.max_memory_entries:], f, ensure_ascii=False, indent=2)

    # ------------------ 共用回覆發送 ------------------
    async def safe_send(self, message: discord.Message, reply: str = None, file: discord.File = None):
        """安全送出文字或檔案，並避開 Discord 長度限制。"""
        if not reply and not file:
            return

        try:
            if file:
                await message.channel.send(content=reply[:1900] if reply else None, file=file)
                return

            # 短回覆逐行送出，降低單則訊息過長的機率。
            if reply.count("\n") < 15:
                # 行數少時逐行送出。
                for line in reply.split("\n"):
                    if not line.strip():
                        continue
                    try:
                        await message.channel.send(line[:1900])  # 預留空間避免超過 2000 字限制。
                    except:
                        continue
            else:
                # 行數多時改送單段摘要。
                try:
                    await message.channel.send(reply[:1900])
                except:
                    await message.channel.send("-# Hmmm. Something went wrong.")

        except Exception as e:
            print(f"❌ Send error: {e}")

    # ------------------ 自動回覆 ------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        self.message_buffer.append(f"{message.author.name}: {message.content}")

        if isinstance(message.channel, discord.DMChannel):
            await self.try_chat_reply(message)
            return

        if self.bot.user in message.mentions:
            await self.try_chat_reply(message)
        elif message.reference:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg.author.id == self.bot.user.id:
                    await self.try_chat_reply(message)
            except Exception as e:
                print(f"❌ Failed to fetch referenced message: {e}")

    async def try_chat_reply(self, message: discord.Message):
        if not self.client:
            await self.safe_send(message, reply="Gemini 尚未設定完成，請檢查 GEMINI_API_KEY。")
            return

        
        # 使用「生成」前綴時改走圖片生成流程。
        if message.content.startswith("生成"):
            prompt = message.content[2:].strip()
            
            if not prompt:
                 await self.safe_send(message, reply="請在「生成」後面加上你想要畫的內容喔！")
                 return

            print(f"🎨 觸發圖片生成請求: {prompt}")
            try:
                async with message.channel.typing():
                    # 呼叫可回傳圖片資料的 Gemini 生成 API。
                    # 若改用 Imagen，需切換到 generate_images 介面。
                    response = await self.client.aio.models.generate_content(
                        model=self.image_model_name,
                        contents=[prompt],
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"] # 要求模型回傳圖片內容。
                        )
                    )

                    # 從回應中的 parts 找出圖片資料。
                    # 新版結構為 response.candidates[0].content.parts。
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            # inline_data 代表模型直接回傳的圖片位元組。
                            if part.inline_data:
                                # 取得圖片 bytes。
                                image_bytes = part.inline_data.data
                                
                                # 轉成 PIL 圖片物件，確認格式可讀。
                                image = Image.open(io.BytesIO(image_bytes))

                                # 轉成 Discord 可上傳的記憶體檔案。
                                image_buffer = io.BytesIO()
                                image.save(image_buffer, format="PNG")
                                image_buffer.seek(0)

                                discord_file = discord.File(fp=image_buffer, filename="generated_image.png")
                                await self.safe_send(message, reply=f"為您生成：{prompt}", file=discord_file)
                                print("✅ 圖片發送成功。")
                                return

                    await self.safe_send(message, reply="生成失敗，模型沒有回傳圖片（可能被拒絕或格式錯誤）。")
                    return

            except Exception as e:
                print(f"❌ 圖片生成錯誤: {e}")
                await self.safe_send(message, reply="抱歉，圖片生成過程中發生錯誤，請稍後再試。")
                return

        # 一般文字訊息走聊天回覆流程。
        try:
            async with message.channel.typing():
                async with self.memory_lock:
                    memory = self.load_memory()

                # 使用 types.Content 明確包裝訊息，避免 SDK 版本差異造成格式問題。
                
                # 建立本次使用者訊息。
                current_msg = types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"{message.author.name}: {message.content}")]
                )
                
                # 將 JSON 記憶轉回 SDK 需要的 Content 物件。
                history_contents = []
                for m in memory:
                    parts = []
                    for p in m["parts"]:
                        parts.append(types.Part.from_text(text=p))
                    history_contents.append(types.Content(role=m["role"], parts=parts))

                # 將歷史記憶與本次訊息一起送出。
                full_contents = history_contents + [current_msg]

                response = await self.client.aio.models.generate_content(
                    model=self.text_model_name,
                    contents=full_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=self.prompt, # 系統提示詞統一放在設定中。
                        temperature=0.7
                    )
                )

                reply = response.text.strip()
                await self.safe_send(message, reply)

                # 以 dict 儲存記憶，方便寫入 JSON。
                async with self.memory_lock:
                    memory = self.load_memory()
                    memory.append({"role": "user", "parts": [f"{message.author.name}: {message.content}"]})
                    memory.append({"role": "model", "parts": [reply]})
                    self.save_memory(memory)

        except Exception as e:
            print(f"❌ ChatReply error: {e}")
            await message.reply("抱歉，我剛剛腦袋打結了，請再說一次！")

    # ------------------ 指令 ------------------
    @commands.command(name="forget")
    async def forget(self, ctx):
        """清除目前共用的對話記憶。"""
        async with self.memory_lock:
            self.save_memory([])
        await ctx.send("好啦，我把所有對話都忘掉了 😵‍💫")

# ------------------ 啟動 ------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(GeminiChat(bot))
    print("✅ GeminiChat cog has been loaded successfully!")
