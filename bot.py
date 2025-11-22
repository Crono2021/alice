import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("BOT_TOKEN recibido:", BOT_TOKEN)

CLEAN_REGEX = r"(@\S+|#\S+|https?://\S+|www\.\S+)"

# Archivo persistente
USERS_FILE = "/data/usuarios.json"

# -----------------------------
# CARGA Y GUARDADO DE USUARIOS
# -----------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    os.makedirs("/data", exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

registered_users = load_users()

# Estados de usuario
user_states = {}

OWNER_ID = 5540195020


# -----------------------------
# MENSAJE DE BIENVENIDA
# -----------------------------
async def send_welcome_message(update: Update):
    await update.message.reply_text(
        "Bienvenido. Este bot sirve para limpiar y organizar captions de forma rápida.\n\n"
        "Comandos disponibles:\n\n"
        "/temporada X\n"
        "Inicia un modo en el que los archivos que envíes serán numerados con el formato Xx01, Xx02, etc.\n"
        "Ejemplo: /temporada 2\n\n"
        "/borrar TEXTO\n"
        "Activa un modo en el que el bot eliminará ese texto exacto de todos los captions de los archivos que envíes.\n"
        "Ejemplo: /borrar [1080p h264 Web-DL]\n\n"
        "/finalizar\n"
        "Sale del modo temporada o del modo borrar y vuelve al funcionamiento normal.\n\n"
        "Además, el bot limpia automáticamente menciones (@), hashtags (#) y enlaces en los captions para mantenerlos ordenados."
    )


# -----------------------------
# REGISTRO DE USUARIOS
# -----------------------------
async def register_user(update: Update):
    """Registrar usuario y mostrar bienvenida si es primera vez."""
    user = update.message.from_user
    user_id = str(user.id)

    first_time = user_id not in registered_users

    if first_time:
        registered_users[user_id] = {
            "name": user.full_name,
            "username": f"@{user.username}" if user.username else "",
            "id": user.id
        }
        save_users(registered_users)
        await send_welcome_message(update)


# -----------------------------
# COMANDO /usuarios (solo owner)
# -----------------------------
async def cmd_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        return await update.message.reply_text("No tienes permiso para usar este comando.")

    if not registered_users:
        return await update.message.reply_text("No hay usuarios registrados.")

    texto = "Usuarios registrados:\n\n"
    for uid, info in registered_users.items():
        texto += f"{info['name']}\n"
        texto += f"ID: {info['id']}\n"
        texto += f"Usuario: {info['username']}\n\n"

    await update.message.reply_text(texto)


# -----------------------------
# LIMPIEZA DE CAPTION
# -----------------------------
def clean_caption(caption: str) -> str:
    if not caption:
        return ""
    cleaned = re.sub(CLEAN_REGEX, "", caption)
    cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
    cleaned = "\n".join([line for line in cleaned.splitlines() if line.strip()])
    return cleaned


# -----------------------------
# COMANDO /temporada
# -----------------------------
async def cmd_temporada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    await register_user(update)

    if len(context.args) != 1 or not context.args[0].isdigit():
        return await update.message.reply_text("Uso correcto: /temporada 1")

    season = int(context.args[0])
    user_id = update.message.from_user.id

    user_states[user_id] = user_states.get(user_id, {})
    user_states[user_id]["season"] = season
    user_states[user_id]["counter"] = 1

    await update.message.reply_text(
        f"Temporada {season} iniciada.\nEnvía los archivos para numerarlos."
    )


# -----------------------------
# COMANDO /borrar
# -----------------------------
async def cmd_borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    await register_user(update)

    if len(context.args) == 0:
        return await update.message.reply_text(
            "Uso correcto: /borrar TEXTO\nEjemplo: /borrar [1080p h264 Web-DL]"
        )

    text_to_delete = " ".join(context.args)
    user_id = update.message.from_user.id

    user_states[user_id] = user_states.get(user_id, {})
    user_states[user_id]["delete_mode"] = True
    user_states[user_id]["delete_text"] = text_to_delete

    await update.message.reply_text(
        f"Modo borrar activado.\n"
        f"Texto a eliminar: '{text_to_delete}'\n\n"
        "Envíame ahora todos los archivos cuyos captions quieras limpiar.\n"
        "Cuando termines, usa /finalizar"
    )


# -----------------------------
# COMANDO /finalizar
# -----------------------------
async def cmd_finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    await register_user(update)

    user_id = update.message.from_user.id

    if user_id in user_states:
        user_states[user_id].clear()

    await update.message.reply_text("Proceso finalizado. El bot vuelve al modo normal.")


# -----------------------------
# MANEJO DE ARCHIVOS
# -----------------------------
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    await register_user(update)

    user_id = update.message.from_user.id
    state = user_states.get(user_id, {})

    caption_original = update.message.caption or ""
    caption_limpio = clean_caption(caption_original)
    final_caption = caption_limpio

    if state.get("delete_mode"):
        delete_text = state.get("delete_text", "")
        final_caption = final_caption.replace(delete_text, "").strip()

    if "season" in state:
        season = state["season"]
        counter = state["counter"]
        final_caption = f"{season}x{counter:02d} - {final_caption}".strip()
        user_states[user_id]["counter"] += 1

    if update.message.video:
        await update.message.reply_video(video=update.message.video.file_id, caption=final_caption)
    elif update.message.document:
        await update.message.reply_document(document=update.message.document.file_id, caption=final_caption)


# -----------------------------
# MENSAJES DE TEXTO NORMALES
# -----------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await register_user(update)


# -----------------------------
# MAIN
# -----------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("temporada", cmd_temporada))
    app.add_handler(CommandHandler("borrar", cmd_borrar))
    app.add_handler(CommandHandler("finalizar", cmd_finalizar))
    app.add_handler(CommandHandler("usuarios", cmd_usuarios))

    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()


if __name__ == "__main__":
    main()
