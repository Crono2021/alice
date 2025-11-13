import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("BOT_TOKEN recibido:", BOT_TOKEN)

CLEAN_REGEX = r"(@\S+|#\S+|https?://\S+|www\.\S+)"

def clean_caption(caption: str) -> str:
    if not caption:
        return ""
    cleaned = re.sub(CLEAN_REGEX, "", caption)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    caption_original = message.caption or ""
    caption_limpio = clean_caption(caption_original)

    if message.video:
        await message.reply_video(
            video=message.video.file_id,
            caption=caption_limpio
        )
    elif message.document:
        await message.reply_document(
            document=message.document.file_id,
            caption=caption_limpio
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))
    app.run_polling()

if __name__ == "__main__":
    main()
