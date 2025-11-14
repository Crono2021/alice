import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import re

# Obtener token desde variables de entorno (Railway)
BOT_TOKEN = os.getenv("BOT_TOKEN")
print("BOT_TOKEN recibido:", BOT_TOKEN)

# Regex que elimina menciones, hashtags y enlaces
CLEAN_REGEX = r"(@\S+|#\S+|https?://\S+|www\.\S+)"

def clean_caption(caption: str) -> str:
    """
    Eliminar menciones (@usuario), hashtags (#tag) y enlaces (http/https/www)
    """
    if not caption:
        return ""
    cleaned = re.sub(CLEAN_REGEX, "", caption)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # Ignorar TODO lo que no sea chat privado
    if message.chat.type != "private":
        return

    caption_original = message.caption or ""
    caption_limpio = clean_caption(caption_original)

    # Si es video
    if message.video:
        await message.reply_video(
            video=message.video.file_id,
            caption=caption_limpio
        )

    # Si es archivo/documento
    elif message.document:
        await message.reply_document(
            document=message.document.file_id,
            caption=caption_limpio
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handler para videos y documentos
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    app.run_polling()

if __name__ == "__main__":
    main()
