import os, logging, requests, datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# --- DATABASE TEMP (en mémoire, après on mettra Postgres) ---
users_db = {} # user_id: {"lang": "fr", "wins": 0, "dette": 0.0, "is_blocked": False}

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"lang": "fr", "wins": 0, "dette": 0.0, "is_blocked": False, "free_hours_today": 0}
    return users_db[user_id]

# --- MESSAGES /START ---
MESSAGES = {
    "fr": "Salut ami 👋 Je vais t'accompagner dans ton aventure de trading pour te rendre rentable.\n\nJe peux:\n📊 /analyse - Te donner les 3 meilleurs marchés du moment avec 2 TP et 2 SL\n🔔 Activer les alertes de hausse/baisse\n💰 Version gratuite: 5h/jour\n\nChoisis ta langue: /lang fr ou /lang en",
    "en": "Hi friend 👋 I will guide you through your trading journey to make you profitable.\n\nI can:\n📊 /analyse - Give you the 3 best markets to trade with 2 TP and 2 SL\n🔔 Enable pump/dump alerts\n💰 Free version: 5h/day\n\nChoose language: /lang fr or /lang en"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    lang = user["lang"]
    await update.message.reply_text(MESSAGES[lang])

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if context.args and context.args[0] in ["fr", "en"]:
        user["lang"] = context.args[0]
        await update.message.reply_text(f"Langue changée en {context.args[0]} ✅" if context.args[0]=="fr" else "Language changed to en ✅")
    else:
        await update.message.reply_text("Utilise: /lang fr ou /lang en")
    await start(update, context)

# Test simple pour garder le 200 OK
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Reçu: {update.message.text} (tape /start pour commencer)")

if __name__ == "__main__":
    print("Josh Business Bot V5 Etape 1 - 24h/24")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.run_polling()
