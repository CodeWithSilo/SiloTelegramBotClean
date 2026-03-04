


import os
import yt_dlp
import requests
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# -------------------------
# CONFIGURATION
# -------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
FLW_PUBLIC_KEY = os.getenv("FLW_PUBLIC_KEY")
FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY") # Flutterwave secret key

# Store premium users {chat_id: expiry_datetime}
premium_users = {}

# Flask app for webhook
app = Flask(__name__)

# -------------------------
# TELEGRAM BOT HANDLERS
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Silo!\nSend a video link from YouTube, TikTok, Instagram, or Facebook.\n"
        "Free users can download 360p. Premium users unlock 720p/1080p."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat_id
    now = datetime.now()
    expiry = premium_users.get(chat_id)
    is_premium = expiry and expiry > now

    # Buttons
    buttons = [
        [InlineKeyboardButton("360p (Free)", callback_data=f"360|{url}")],
        [InlineKeyboardButton("720p (Premium)", callback_data=f"720|{url}")],
        [InlineKeyboardButton("1080p (Premium)", callback_data=f"1080|{url}")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    # Try to get thumbnail
    thumbnail_url = None
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            thumbnail_url = info.get("thumbnail")
    except:
        pass

    if thumbnail_url:
        await update.message.reply_photo(photo=thumbnail_url, caption="Choose download quality:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Choose download quality:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    data = query.data.split("|")
    quality, url = data[0], data[1]

    now = datetime.now()
    expiry = premium_users.get(chat_id)

    # Premium check
    if quality in ["720", "1080"]:
        if not expiry or expiry < now:
            pay_link = create_flutterwave_link(chat_id)
            await query.message.reply_text(
                f"🔒 Premium quality requires ₦550/day.\nPay here: {pay_link}\n"
                "After payment, premium unlocks automatically."
            )
            return

    await query.message.reply_text("Downloading video... ⏳")
    download_video(query, url, quality)

# -------------------------
# VIDEO DOWNLOAD FUNCTION
# -------------------------
def download_video(query, url, quality):
    ydl_opts = {
        'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]',
        'outtmpl': 'video.%(ext)s',
        'merge_output_format': 'mp4',
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # Telegram file size limit ~50MB
        if os.path.getsize(filename) > 50 * 1024 * 1024:
            query.message.reply_text("❌ File too large. Try lower quality.")
            os.remove(filename)
            return

        query.bot.send_video(chat_id=query.message.chat_id, video=open(filename, 'rb'))
        os.remove(filename)
    except:
        query.message.reply_text("❌ Download failed.")

# -------------------------
# FLUTTERWAVE PAYMENT LINK
# -------------------------
def create_flutterwave_link(user_id):
    headers = {"Authorization": f"Bearer {FLW_SECRET_KEY}"}
    tx_ref = f"silo_{user_id}_{int(datetime.now().timestamp())}"
    data = {
        "tx_ref": tx_ref,
        "amount": 550,
        "currency": "NGN",
        "redirect_url": "https://your-render-url.com/flutterwave-webhook",  # CHANGE THIS
        "payment_options": "card,bank,ussd,qr",
        "customer": {"email": f"user{user_id}@example.com"},
        "customizations": {"title": "Silo Premium", "description": "Daily premium video download"}
    }
    resp = requests.post("https://api.flutterwave.com/v3/payments", json=data, headers=headers)
    return resp.json()["data"]["link"]

# -------------------------
# FLASK WEBHOOK (AUTOMATIC PAYMENT CONFIRMATION)
# -------------------------
@app.route("/flutterwave-webhook", methods=["POST"])
def flutterwave_webhook():
    data = request.json
    tx_ref = data.get("tx_ref")
    status = data.get("status")
    try:
        user_id = int(tx_ref.split("_")[1])
        if status == "successful":
            premium_users[user_id] = datetime.now() + timedelta(hours=24)
            print(f"✅ Premium unlocked for {user_id}")
    except:
        pass
    return "OK", 200

# -------------------------
# RUN TELEGRAM BOT
# -------------------------
def run_bot():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_telegram.add_handler(CallbackQueryHandler(button_handler))
    print("🚀 Silo bot is running...")
    app_telegram.run_polling()

# -------------------------
# RUN BOTH FLASK AND TELEGRAM
# -------------------------
if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()
    run_bot()