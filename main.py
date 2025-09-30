import os
import discord
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
import threading

# ----------------------
# 1) Keep-alive server (Render free plan hack)
# ----------------------
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run).start()

# ----------------------
# 2) Ortam değişkenlerini yükle
# ----------------------
load_dotenv()
DISCORD_TOKEN   = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY  = os.getenv('GEMINI_API_KEY')

# ----------------------
# 3) Gemini istemcisini başlat
# ----------------------
genai.configure(api_key=GEMINI_API_KEY)

# ----------------------
# 4) Bot tanımı
# ----------------------
intents = discord.Intents(
    guilds=True,
    guild_messages=True,
    message_content=True
)
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Bot hazır: {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    print(f"Gelen mesaj: {message.content}")
    await bot.process_commands(message)

@bot.command(name='ping')
async def ping(ctx):
    print("📨 ping komutu alındı")
    await ctx.reply("pong")

# ----------------------
# 5) URL’den makale içeriği çekme
# ----------------------
def fetch_article_text(url):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    paras = soup.find_all('p')
    text = "\n".join(p.get_text() for p in paras)
    return text[:3000]  # Token sınırları için kısalt

# ----------------------
# 6) Gelişmiş Gemini prompt’ları
# ----------------------
SYSTEM_PROMPT = """
You are a professional summarization assistant.
Your task is to read an English article and produce a concise, coherent summary in Turkish.
Focus on the main ideas, preserve essential details, use clear and fluent Turkish,
and keep the summary under 100 words whenever possible.
"""

USER_PROMPT_TEMPLATE = """
Please summarize the following English text in Turkish:
{text} """

# ----------------------
# 7) !ozet komutu
# ----------------------
@bot.command(name='ozet')
async def ozet(ctx, url: str):
    if not (url.startswith("http://") or url.startswith("https://")):
        return await ctx.reply("❗ Lütfen geçerli bir bağlantı girin (http:// veya https:// ile başlamalı).")

    reply = await ctx.reply("🔄 Özet oluşturuluyor, lütfen bekleyin…")

    # 1) İçeriği çek
    try:
        article = fetch_article_text(url)
    except Exception as e:
        return await reply.edit(content=f"❌ Makale çekilirken hata: {e}")

    # 2) Gemini ile özet oluştur
    prompt = USER_PROMPT_TEMPLATE.format(text=article)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        chat = model.start_chat()
        response = chat.send_message(f"{SYSTEM_PROMPT}\n\n{prompt}")
        summary = response.text.strip()
    except Exception as e:
        return await reply.edit(content=f"❌ Özetlenirken hata: {e}")

    # 3) Sonucu gönder
    embed = discord.Embed(
        title="📝 Türkçe Özet",
        description=summary,
        color=discord.Color.green()
    )
    await reply.edit(content=None, embed=embed)

# ----------------------
# 8) Botu çalıştır
# ----------------------
bot.run(DISCORD_TOKEN)
