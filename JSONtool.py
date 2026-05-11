import discord
import json
import asyncio
import os
import dotenv
from dotenv import load_dotenv
load_dotenv()  # 載入本機環境變數。



TOKEN = os.getenv('DISCORD_TOKEN')  # 從環境變數讀取 Discord bot token。
CHANNEL_ID = 1203004081187070045  # 要備份訊息的 Discord 頻道 ID。
TARGET_USERNAME = 'koala._.lol'  # 篩選目標 username，不是伺服器暱稱。
MAX_MESSAGES = 5000  # 最多讀取的歷史訊息數量。
FILTER_ONLY = True   # True 時只輸出目標使用者的訊息。

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'🔗 登入成功：{client.user}')
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("❌ 找不到頻道")
        await client.close()
        return

    all_messages = []
    matched_messages = []

    async for msg in channel.history(limit=MAX_MESSAGES, oldest_first=False):
        entry = {
            'author': msg.author.name,
            'content': msg.content,
            'timestamp': msg.created_at.isoformat()
        }
        all_messages.append(entry)

        if msg.author.name == TARGET_USERNAME:
            matched_messages.append(entry)

    if FILTER_ONLY:
        data_to_save = matched_messages
        print(f'✅ 篩選 {TARGET_USERNAME} 的訊息共 {len(matched_messages)} 則')
    else:
        data_to_save = all_messages
        print(f'✅ 共擷取 {len(all_messages)} 則訊息（含全部使用者）')

    with open('filtered_messages.json', 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

    print('💾 備份完成，已儲存至 filtered_messages.json')
    await client.close()

client.run(TOKEN)
