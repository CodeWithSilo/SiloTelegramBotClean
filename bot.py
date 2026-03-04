
import os
import requests
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

TOKEN = "8799832660:AAGCPrexiWjTgyVKsKp2gtxfB1ixBdJhV98"


# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Silo!\n\n"
        "Send me a video link from:\n"
        "• TikTok\n"
        "• YouTube\n"
        "• Instagram\n"
        "• Facebook\n\n"
        "I’ll download it for you 🎥🔥"
    )

# TikTok Special Handler
async def download_tiktok(update, url):
    await update.message.reply_text("Downloading TikTok video... ⏳")

    try:
        api = f"https://tikwm.com/api/?url={url}"
        response = requests.get(api).json()

        video_url = response["data"]["play"]

        await update.message.reply_video(video_url)

    except:
        await update.message.reply_text("❌ Failed to download TikTok video.")

# General Downloader (YouTube, IG, FB)
async def download_general(update, url):
    await update.message.reply_text("Downloading video... ⏳")

    try:
        ydl_opts = {
    'format': 'best',
    'outtmpl': 'video.%(ext)s',
    'cookiefile': 'cookies.txt',
    'quiet': True
    }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await update.message.reply_video(video=open(filename, 'rb'))

        os.remove(filename)

    except:
        await update.message.reply_text("❌ Failed to download video.")

# Main Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    if "tiktok.com" in url:
        await download_tiktok(update, url)
    elif any(site in url for site in ["youtube.com", "youtu.be", "instagram.com", "facebook.com"]):
        await download_general(update, url)
    else:
        await update.message.reply_text("⚠️ Unsupported link.")

# Build App
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Silo is running 🚀")
app.run_polling()