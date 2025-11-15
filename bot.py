import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("BOT_TOKEN recibido:", BOT_TOKEN)

# Regex que elimina menciones, hashtags y enlaces
CLEAN_REGEX = r"(@\S+|#\S+|https?://\S+|www\.\S+)"

# Estado por usuario: { user_id: {"season": int, "counter": int} }
user_states = {}

def clean_caption(caption: str) -> str:
    if not caption:
        return ""
    cleaned = re.sub(CLEAN_REGEX, "", caption)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# -------------------------------
#   COMANDOS
# -------------------------------

async def cmd_temporada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activar temporada y reiniciar contador"""
    message = update.message

    if message.chat.type != "private":
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await message.reply_text("Uso correcto: /temporada 1")
        return

    season = int(context.args[0])
    user_id = message.from_user.id

    user_states[user_id] = {"season": season, "counter": 1}

    await message.reply_text(f"Temporada {season} iniciada. Envía los archivos para enumerarlos.")


async def cmd_finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Desactivar temporada"""
    message = update.message

    if message.chat.type != "private":
        return

    user_id = message.from_user.id

    if user_id in user_states:
        del user_states[user_id]

    await message.reply_text("Numeración finalizada. El bot vuelve a modo normal.")


# -------------------------------
#   MANEJO DE ARCHIVOS
# -------------------------------

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    caption_original = message.caption or ""
    caption_limpio = clean_caption(caption_original)

    prefix = ""

    # Si el usuario tiene temporada activa → generar prefijo
    if user_id in user_states:
        season = user_states[user_id]["season"]
        counter = user_states[user_id]["counter"]

        prefix = f"{season}x{counter:02d} - "
        user_states[user_id]["counter"] += 1

    final_caption = f"{prefix}{caption_limpio}".strip()

    # Enviar video procesado
    if message.video:
        await message.reply_video(
            video=message.video.file_id,
            caption=final_caption
        )

    # Enviar documento procesado
    elif message.document:
        await message.reply_document(
            document=message.document.file_id,
            caption=final_caption
        )


# -------------------------------
#   MAIN
# -------------------------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("temporada", cmd_temporada))
    app.add_handler(CommandHandler("finalizar", cmd_finalizar))

    # Archivos y videos
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    app.run_polling()


if __name__ == "__main__":
    main()
