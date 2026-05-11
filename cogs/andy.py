import datetime
import discord
from discord.ext import commands
from discord import app_commands
import os

QUOTES_IMG_FOLDER = "./quotes_img"

class QuoteSlashCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="安迪語錄", description="顯示圖片語錄")
    @app_commands.describe(quote_name="輸入語錄名稱")
    async def quote_image(self, interaction: discord.Interaction, quote_name: str):
        for ext in [".png", ".jpg", ".jpeg"]:
            filepath = os.path.join(QUOTES_IMG_FOLDER, f"{quote_name}{ext}")
            if os.path.isfile(filepath):
                # 建立 Discord 可傳送的檔案物件。
                file = discord.File(filepath, filename=os.path.basename(filepath))
                
                # 直接傳送圖片檔，不使用嵌入訊息。
                await interaction.response.send_message(file=file)
                return
            # 找不到檔案時回覆錯誤訊息。
        await interaction.response.send_message(f"❌ 找不到圖片語錄「{quote_name}」", ephemeral=True)

    # 依目前輸入內容自動補全語錄名稱。
    @quote_image.autocomplete("quote_name")
    async def quote_autocomplete(self, interaction: discord.Interaction, current: str):
        options = []
        for fname in os.listdir(QUOTES_IMG_FOLDER):
            name, ext = os.path.splitext(fname)
            if ext.lower() in [".png", ".jpg", ".jpeg"] and current in name:
                options.append(app_commands.Choice(name=name, value=name))
        return options[:20] # Discord 自動補全最多回傳 20 筆。

async def setup(bot):
    await bot.add_cog(QuoteSlashCog(bot))
    print("✅ QuoteSlashCog has been loaded successfully!")
