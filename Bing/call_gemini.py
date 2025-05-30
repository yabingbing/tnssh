from dotenv import load_dotenv
import google.generativeai as genai
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("gemini_api_key")

# 初始化模型
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")

def call_gemini(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text.strip()
