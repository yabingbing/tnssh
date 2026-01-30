import discord
from discord.ext import commands
import os
import json
import io
from collections import deque
from dotenv import load_dotenv
from PIL import Image

# 新版 SDK
from google import genai
from google.genai import types

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
        self.message_buffer = deque(maxlen=15)  # 短期對話緩衝
        self.prompt = self.load_prompt()

        # 初始化 Gemini Client (新版寫法)
        try:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            # 設定預設使用的文字模型
            self.text_model_name = "gemini-2.5-flash" 
            # 設定畫圖用的模型 (如果是 Gemini 2.0 可直接用同一個，或是指定 Imagen)
            self.image_model_name = "gemini-2.5-flash" 
            
            print(f"✅ Gemini Client initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to configure Gemini Client: {e}")
            self.client = None

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

    def load_memory(self):
        with open(MEMORY_FILE, 'r', encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_memory(self, memory):
        with open(MEMORY_FILE, 'w', encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

    # ------------------ 共用回覆發送 ------------------
    async def safe_send(self, message: discord.Message, reply: str = None):
        """安全發送訊息 - 純文字版"""
        if not reply:
            return

        try:
            # 這裡就是你要保留的邏輯 👇
            if reply.count("\n") < 15:
                # 行數少，逐行送
                for line in reply.split("\n"):
                    if not line.strip():
                        continue
                    try:
                        await message.channel.send(line[:1900])  # Discord 限制 2000 字
                    except:
                        continue
            else:
                # 行數多，整段送
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
        
        # 🎨 圖片生成邏輯
        if message.content.startswith("生成"):
            prompt = message.content[2:].strip()
            
            if not prompt:
                 await self.safe_send(message, reply="請在「生成」後面加上你想要畫的內容喔！")
                 return

            print(f"🎨 觸發圖片生成請求: {prompt}")
            try:
                async with message.channel.typing():
                    # 呼叫新版 API (gemini-2.0 支援直接輸出圖片)
                    # 注意：如果之後要用 Imagen 3，要改用 client.models.generate_images
                    response = await self.client.aio.models.generate_content(
                        model=self.image_model_name,
                        contents=[prompt],
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"] # 強制要求輸出圖片
                        )
                    )

                    # 處理回傳的圖片資料
                    # 新版結構 response.candidates[0].content.parts
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            # 檢查是否有 inline_data (圖片 bytes)
                            if part.inline_data:
                                # 1. 取得 Bytes 資料
                                image_bytes = part.inline_data.data
                                
                                # 2. 轉成 PIL Image
                                image = Image.open(io.BytesIO(image_bytes))

                                # 3. 轉存成 BytesIO 給 Discord 用
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

        # 💬 一般文字對話邏輯
        try:
            async with message.channel.typing():
                memory = self.load_memory()

                # 新版 content 結構轉換
                # 舊版: [{"role": "user", "parts": ["text"]}]
                # 新版其實差不多，但為了保險我們用 types.Content 來包裝會比較嚴謹，
                # 不過傳 dict 給 google-genai 也是會通的。
                
                # 建構這次的請求內容
                current_msg = types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"{message.author.name}: {message.content}")]
                )
                
                # 轉換記憶格式 (雖然 dict 通常可以，但用物件比較穩)
                history_contents = []
                for m in memory:
                    parts = []
                    for p in m["parts"]:
                        parts.append(types.Part.from_text(text=p))
                    history_contents.append(types.Content(role=m["role"], parts=parts))

                # 合併歷史與當前訊息
                full_contents = history_contents + [current_msg]

                response = await self.client.aio.models.generate_content(
                    model=self.text_model_name,
                    contents=full_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=self.prompt, # System Prompt 放這裡
                        temperature=0.7
                    )
                )

                reply = response.text.strip()
                await self.safe_send(message, reply)

                # 存進短期記憶 (維持存 dict 格式，方便 JSON 序列化)
                memory.append({"role": "user", "parts": [f"{message.author.name}: {message.content}"]})
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