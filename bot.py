import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("BOT_TOKEN recibido:", BOT_TOKEN)

CLEAN_REGEX = r"(@\S+|#\S+|https?://\S+|www\.\S+)"

# Estados del usuario
# user_states = {
#   user_id: {
#       "season": int | None,
#       "counter": int,
#       "delete_mode": bool,
#       "delete_text": str
#   }
# }
user_states = {}

# -------------------------------------------------------
# LIMPIEZA DE CAPTION (RESPETA FORMATO Y SALTOS DE LÍNEA)
# -------------------------------------------------------

def clean_caption(caption: str) -> str:
    if not caption:
        return ""

    cleaned = re.sub(CLEAN_REGEX, "", caption)
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
    cleaned = "\n".join([line for line in cleaned.splitlines() if line.strip()])

    return cleaned


# -------------------------------------------------------
# COMANDO /temporada
# -------------------------------------------------------
async def cmd_temporada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.chat.type != "private":
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await message.reply_text("Uso correcto: /temporada 1")
        return

    season = int(context.args[0])
    user_id = message.from_user.id

    user_states[user_id] = user_states.get(user_id, {})
    user_states[user_id]["season"] = season
    user_states[user_id]["counter"] = 1

    await message.reply_text(
        f"Temporada {season} iniciada.\nEnvía los archivos para numerarlos."
    )


# -------------------------------------------------------
# COMANDO /borrar
# -------------------------------------------------------
async def cmd_borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.chat.type != "private":
        return

    if len(context.args) == 0:
        await message.reply_text("Uso correcto: /borrar TEXTO\nEjemplo: /borrar [1080p h264 Web-DL]")
        return

    text_to_delete = " ".join(context.args)
    user_id = message.from_user.id

    user_states[user_id] = user_states.get(user_id, {})
    user_states[user_id]["delete_mode"] = True
    user_states[user_id]["delete_text"] = text_to_delete

    await message.reply_text(
        f"Modo borrar activado.\n"
        f"Texto a eliminar: '{text_to_delete}'\n\n"
        "Envíame ahora todos los archivos cuyos captions quieras limpiar.\n"
        "Cuando termines, usa /finalizar"
    )


# -------------------------------------------------------
# COMANDO /finalizar
# -------------------------------------------------------
async def cmd_finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.chat.type != "private":
        return

    user_id = message.from_user.id

    if user_id in user_states:
        user_states[user_id].pop("delete_mode", None)
        user_states[user_id].pop("delete_text", None)
        user_states[user_id].pop("season", None)
        user_states[user_id].pop("counter", None)

    await message.reply_text("Proceso finalizado. El bot vuelve al modo normal.")


# -------------------------------------------------------
# MANEJO DE ARCHIVOS / VIDEOS
# -------------------------------------------------------
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    state = user_states.get(user_id, {})

    caption_original = message.caption or ""
    caption_limpio = clean_caption(caption_original)

    final_caption = caption_limpio

    # ---------- MODO BORRAR ----------
    if state.get("delete_mode"):
        delete_text = state.get("delete_text", "")
        if delete_text:
            final_caption = final_caption.replace(delete_text, "").strip()

    # ---------- MODO TEMPORADA ----------
    if "season" in state:
        season = state["season"]
        counter = state["counter"]
        prefix = f"{season}x{counter:02d} - "

        final_caption = f"{prefix}{final_caption}".strip()
        user_states[user_id]["counter"] += 1

    # Enviar archivo limpio
    if message.video:
        await message.reply_video(video=message.video.file_id, caption=final_caption)

    elif message.document:
        await message.reply_document(document=message.document.file_id, caption=final_caption)


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("temporada", cmd_temporada))
    app.add_handler(CommandHandler("borrar", cmd_borrar))
    app.add_handler(CommandHandler("finalizar", cmd_finalizar))

    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    app.run_polling()


if __name__ == "__main__":
    main()
