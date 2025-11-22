import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("BOT_TOKEN recibido:", BOT_TOKEN)

CLEAN_REGEX = r"(@\S+|#\S+|https?://\S+|www\.\S+)"

# Ruta del archivo persistente en Railway
USERS_FILE = "/data/usuarios.json"

# Cargar usuarios almacenados
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

# Guardar usuarios
def save_users(data):
    os.makedirs("/data", exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Diccionario en memoria
registered_users = load_users()

# Estados del usuario
user_states = {}

# -------------------------------------------------------
# LIMPIEZA DE CAPTION
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
# REGISTRO DE USUARIOS
# -------------------------------------------------------

def register_user(update: Update):
    """Guarda en archivo JSON todos los usuarios que usen el bot."""
    user = update.message.from_user
    user_id = str(user.id)

    if user_id not in registered_users:
        registered_users[user_id] = {
            "name": user.full_name,
            "username": f"@{user.username}" if user.username else "",
            "id": user.id
        }
        save_users(registered_users)


# -------------------------------------------------------
# COMANDO /usuarios (solo owner)
# -------------------------------------------------------

OWNER_ID = 5540195020

async def cmd_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.from_user.id != OWNER_ID:
        return await message.reply_text("No tienes permiso para usar este comando.")

    if not registered_users:
        return await message.reply_text("No hay usuarios registrados.")

    texto = "📌 *Usuarios registrados:*\n\n"
    for uid, info in registered_users.items():
        texto += f"👤 *{info['name']}*\n"
        texto += f"   🧩 ID: `{info['id']}`\n"
        texto += f"   🔗 Usuario: {info['username']}\n\n"

    await message.reply_text(texto, parse_mode="Markdown")


# -------------------------------------------------------
# COMANDO /temporada
# -------------------------------------------------------
async def cmd_temporada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.chat.type != "private":
        return

    register_user(update)

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

    register_user(update)

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

    register_user(update)

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

    register_user(update)

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
    app.add_handler(CommandHandler("usuarios", cmd_usuarios))

    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))

    app.run_polling()


if __name__ == "__main__":
    main()
