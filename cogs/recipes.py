import discord
from discord import app_commands
from discord.ext import commands
import os
import random

class Recipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recipe_dir = "images/recipes"

    def get_recipe_from_folder(self, folder_path):
        images = [f for f in os.listdir(folder_path) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        if not images:
            return None
        image_file = random.choice(images)
        name = os.path.splitext(image_file)[0]
        txt_path = os.path.join(folder_path, f"{name}.txt")
        description = None
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                description = f.read()
        return name, os.path.join(folder_path, image_file), description

    @app_commands.command(name="食譜", description="從食譜資料夾中隨機抽出一道食譜")
    @app_commands.describe(category="食譜分類，例如：甜點、正餐、小吃")
    async def recipe(self, interaction: discord.Interaction, category: str = None):
        await interaction.response.defer()

        # 決定要搜尋的資料夾
        if category:
            folder_path = os.path.join(self.recipe_dir, category)
            if not os.path.exists(folder_path):
                await interaction.followup.send(f"❌ 沒有找到「{category}」這個分類喔！")
                return
            folders = [folder_path]
        else:
            # 如果沒輸入分類就從所有資料夾中抽
            folders = []
            for root, _, _ in os.walk(self.recipe_dir):
                folders.append(root)

        # 開始隨機挑一張圖片
        random.shuffle(folders)
        for path in folders:
            result = self.get_recipe_from_folder(path)
            if result:
                name, image_path, description = result
                file = discord.File(image_path, filename=os.path.basename(image_path))
                embed = discord.Embed(
                    title=f"📘 食譜：{name}",
                    description=description or "這道食譜目前沒有說明喔～",
                    color=discord.Color.green()
                )
                embed.set_image(url=f"attachment://{os.path.basename(image_path)}")
                await interaction.followup.send(embed=embed, file=file)
                return

        await interaction.followup.send("❌ 沒有找到任何圖片喔！")

async def setup(bot):
    await bot.add_cog(Recipe(bot))
