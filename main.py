import os
import subprocess
import requests
from telegram import Update, Document
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from config import AUTHORIZATION_TOKEN, USER_AGENT, REFERER, SIGNED_URL_API, DOWNLOAD_FOLDER

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome!\nSend me a .txt file with video URLs (one per line). I will download them with headers and signed URLs.")

def get_signed_url(original_url):
    try:
        response = requests.get(SIGNED_URL_API + original_url)
        if response.status_code == 200 and 'url' in response.json():
            return response.json()['url']
        else:
            raise Exception("❌ Signed URL not received")
    except Exception as e:
        raise Exception(f"❌ Signed URL fetch failed: {e}")

def run_yt_dlp(signed_url, output_path):
    cmd = [
        "yt-dlp",
        "--add-header", f"Authorization: {AUTHORIZATION_TOKEN}",
        "--add-header", f"User-Agent: {USER_AGENT}",
        "--add-header", f"Referer: {REFERER}",
        "-o", output_path,
        signed_url
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode, result.stderr.decode()

async def handle_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document: Document = update.message.document
    if not document.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Please upload a .txt file only.")
        return

    user_id = str(update.effective_user.id)
    user_folder = os.path.join(DOWNLOAD_FOLDER, user_id)
    os.makedirs(user_folder, exist_ok=True)

    txt_path = os.path.join(user_folder, document.file_name)
    await document.get_file().download_to_drive(txt_path)

    await update.message.reply_text("📥 File received. Processing URLs...")

    with open(txt_path, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for idx, original_url in enumerate(urls, 1):
        try:
            signed_url = get_signed_url(original_url)
            output_file = os.path.join(user_folder, f"video_{idx}.mp4")
            return_code, error = run_yt_dlp(signed_url, output_file)

            if return_code == 0:
                await update.message.reply_text(f"✅ Video {idx} downloaded successfully.")
            else:
                await update.message.reply_text(f"⚠️ Video {idx} failed.\nError:\n{error[:400]}")

        except Exception as e:
            await update.message.reply_text(f"❌ Error with video {idx}:\n{e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FILE_EXTENSION("txt"), handle_txt))

    print("🤖 Bot is running...")
    app.run_polling()
