import os
import discord
from discord.ext import commands
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class AnswerBook(commands.Cog):
    def __init__(self, bot, sheet_id):
        self.bot = bot
        self.sheet_id = sheet_id
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", self.scope)
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open_by_key(self.sheet_id).sheet1
        self.answers = []
        self.load_answers()

        # 註冊 Discord 訊息右鍵選單指令。
        bot.tree.add_command(
            discord.app_commands.ContextMenu(
                name="答案之書",
                callback=self.message_command,
                type=discord.AppCommandType.message
            )
        )

    def load_answers(self):
        """從試算表指定欄位讀取答案清單。"""
        self.answers = self.sheet.col_values(7)[1:]  # 第一列為標題，略過不使用。
        print(f"✅ 載入 {len(self.answers)} 筆答案")

    def add_answer(self, text):
        """將新答案追加到試算表。"""
        self.sheet.append_row([text])
        self.answers.append(text)
        print(f"✅ 新增答案：{text}")

    async def message_command(self, interaction: discord.Interaction, message: discord.Message):
        if not self.answers:
            await interaction.response.send_message("答案之書空空如也！", ephemeral=True)
            return
        answer = random.choice(self.answers)
        question = message.content
        await interaction.response.send_message(f"📘 針對：『{question}』這個問題\n📖 答案之書給了你答案：\n『{answer}』", ephemeral=False)

# Discord 載入此 Cog 時會呼叫 setup。
async def setup(bot):
    # 從環境變數取得答案之書使用的試算表 ID。
    SHEET_ID = os.getenv("sheet_id") 
    await bot.add_cog(AnswerBook(bot, SHEET_ID))
