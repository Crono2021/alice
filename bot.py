import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import re

# Obtener token desde las variables de entorno (Railway)
BOT_TOKEN = os.getenv("BOT_TOKEN")
print("BOT_TOKEN recibido:", BOT_TOKEN)

# Regex que elimina menciones, hashtags y enlaces
CLEAN_REGEX = r"(@\S+|#\S+|https?://\S+|www\.\S+)"

# Estado por usuario: { user_id: {"season": X, "counter": Y} }
user_states = {}

# -------------------------------------------------------
# LIMPIEZA DE CAPTION (RESPETA FORMATO Y SALTOS DE LÍNEA)
# -------------------------------------------------------

def clean_caption(caption: str) -> str:
    if not caption:
        return ""

    # 1. Eliminar menciones, hashtags y enlaces
    cleaned = re.sub(CLEAN_REGEX, "", caption)

    # 2. Corregir dobles espacios sin tocar saltos de línea
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)

    # 3. Limpiar espacios al inicio/final de cada línea
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines())

    # 4. Eliminar líneas vacías duplicadas
    cleaned = "\n".join([line for line in cleaned.splitlines() if line.strip()])

    return cleaned


# -------------------------------
#          COMANDOS
# -------------------------------

async def cmd_temporada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.chat.type != "private":
        return

    # Validar argumento
    if len(context.args) != 1 or not context.args[0].isdigit():
        await message.reply_text("Uso correcto: /temporada 1")
        return

    season = int(context.args[0])
    user_id = message.from_user.id

    # Guardar estado del usuario
    user_states[user_id] = {"season": season, "counter": 1}

    await message.reply_text(
        f"Temporada {season} iniciada.\n"
        f"Envía los archivos para numerarlos."
    )


async def cmd_finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.chat.type != "private":
        return

    user_id = message.from_user.id

    # Borrar estado del usuario
    if user_id in user_states:
        del user_states[user_id]

    await message.reply_text("Numeración finalizada. El bot vuelve al modo normal.")



# -------------------------------
#   MANEJO DE ARCHIVOS / VIDEOS
# -------------------------------

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # Ignorar grupos, canales, etc.
    if message.chat.type != "private":
        return

    caption_original = message.caption or ""
    caption_limpio = clean_caption(caption_original)

    user_id = message.from_user.id
    prefix = ""

    # Si el usuario tiene temporada activa → numerar
    if user_id in user_states:
        season = user_states[user_id]["season"]
        counter = user_states[user_id]["counter"]

        prefix = f"{season}x{counter:02d} - "
        user_states[user_id]["counter"] += 1

    final_caption = f"{prefix}{caption_limpio}".strip()

    # Si es video
    if message.video:
        await message.reply_video(
            video=message.video.file_id,
            caption=final_caption
        )

    # Si es documento (archivo)
    elif message.document:
        await message.reply_document(
            document=message.document.file_id,
            caption=final_caption
        )



# -------------------------------
#             MAIN
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
