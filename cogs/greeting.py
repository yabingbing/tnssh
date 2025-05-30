import json
import discord
from discord.ext import commands
import random
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

sheet_id = os.getenv("sheet_id")  # 請在 .env 檔案中設定 SHEET_ID


class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sheet_id = sheet_id
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

        try:
            self.creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", self.scope)
            self.client = gspread.authorize(self.creds)
            self.sheet = self.client.open_by_key(self.sheet_id).sheet1
            self.quotes_data = self.load_quotes()
            print("✅ 成功連接 Google Sheets")
        except Exception as e:
            print("❌ 無法連接 Google Sheets：", e)
            self.quotes_data = {}

    def load_quotes(self):
        data = self.sheet.get_all_records()
        quotes = {
            "早安": [], "午安": [], "晚安": [],
            "早安提示": [], "午安提示": [], "晚安提示": []
        }
        for row in data:
            if row.get("早安語錄"):
                quotes["早安"].append(row["早安語錄"])
            if row.get("午安語錄"):
                quotes["午安"].append(row["午安語錄"])
            if row.get("晚安語錄"):
                quotes["晚安"].append(row["晚安語錄"])
            if row.get("早安提示"):
                quotes["早安提示"].append(row["早安提示"])
            if row.get("午安提示"):
                quotes["午安提示"].append(row["午安提示"])
            if row.get("晚安提示"):
                quotes["晚安提示"].append(row["晚安提示"])
        return quotes

    def get_greeting_type(self, content):
        if "早安" in content:
            return "早安"
        elif "午安" in content:
            return "午安"
        elif "晚安" in content:
            return "晚安"
        return None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        greeting_type = self.get_greeting_type(message.content)
        if not greeting_type:
            await self.bot.process_commands(message)
            return

        user_id = str(message.author.id)
        quote = random.choice(self.quotes_data.get(greeting_type, ["哈囉！"]))
        tip = random.choice(self.quotes_data.get(f"{greeting_type}提示", ["今天是個適合吃飯的日子。"]))

        response = quote.replace("<@id>", f"<@{user_id}>") + " " 
        # + tip 這個放上去後面會加一串tip
        await message.channel.send(response)
        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Main(bot))
    print("✅ Greeting cog has been loaded successfully!")
