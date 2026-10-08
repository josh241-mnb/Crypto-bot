import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

users_db = {}

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {"lang": "fr", "wins": 0, "dette": 0.0, "is_blocked": False}
    return users_db[user_id]

MESSAGES = {
    "fr": "Salut ami 👋 Je vais t'accompagner dans ton aventure de trading pour te rendre rentable.\n\n📊 Tape /analyse - pour les 3 meilleurs marchés avec 2 TP et 2 SL\n🔔 Alertes hausse/baisse incluses\n💰 Gratuit: 5h/jour\n\nLangue: /lang fr ou /lang en",
    "en": "Hi friend 👋 I will guide you to become profitable.\n\n📊 Type /analyse - for top 3 markets with 2 TP and 2 SL\n🔔 Pump alerts included\n💰 Free: 5h/day"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(MESSAGES[user["lang"]])

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if context.args and context.args[0] in ["fr","en"]:
        user["lang"] = context.args[0]
    await update.message.reply_text(f"Langue: {user['lang']} ✅")
    await start(update, context)

async def analyse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Analyse en cours bro... Je scanne les 3 meilleurs marchés...")
    # Ici on mettra la logique des 3 marchés + 2TP 2SL après

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("BOT_TOKEN manquant!")
        exit(1)
    print("Josh AI V5.1 démarre...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("analyse", analyse))
    app.run_polling(allowed_updates=Update.ALL_TYPES)
