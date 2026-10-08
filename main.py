import os, logging, requests, asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# users_db = {uid: {lang, wins, dette, blocked, chat_id, tier: "free" ou "paid"}}
users_db = {}

def get_user(uid, chat_id=None):
    if uid not in users_db:
        users_db[uid] = {"lang":"fr","wins":0,"dette":0.0,"blocked":False,"chat_id": chat_id, "tier":"free"}
    if chat_id:
        users_db[uid]["chat_id"]=chat_id
    return users_db[uid]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id, update.effective_chat.id)
    tier_txt = "GRATUIT (1 alerte/jour)" if u["tier"]=="free" else "PAYANT (alerte toutes les 3h) 🔥"
    await update.message.reply_text(f"Salut ami 👋 JOSH AI V6.1\n\nTon statut: {tier_txt}\n\n/analyse - scan instant\n/solde - dette {u['dette']}$/7.5$\n/pay - devenir payant")

async def solde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    await update.message.reply_text(f"Statut: {u['tier']}\nWins: {u['wins']} | Dette: {u['dette']}$/7.5$ | Bloqué: {u['blocked']}")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    await update.message.reply_text("💳 Pour passer PAYANT:\n20$/mois ou 80$/an\nContacte @ton_support sur Telegram pour payer.\nAprès paiement tu recevras les alertes toutes les 3h.")

# COMMANDE ADMIN pour toi: /addpaid ID_TELEGRAM
async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Mets ton ID Telegram ici pour sécuriser
    MY_ADMIN_ID = 123456789 # <-- REMPLACE PAR TON ID
    if update.effective_user.id!= MY_ADMIN_ID:
        await update.message.reply_text("Pas autorisé bro.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addpaid 123456789")
        return
    try:
        target_id = int(context.args[0])
        if target_id in users_db:
            users_db[target_id]["tier"]="paid"
            users_db[target_id]["blocked"]=False
            users_db[target_id]["dette"]=0
            await update.message.reply_text(f"User {target_id} passé PAYANT ✅")
            await context.bot.send_message(chat_id=users_db[target_id]["chat_id"], text="🎉 Tu es passé PAYANT! Tu vas recevoir les alertes toutes les 3h maintenant 🔥")
        else:
            await update.message.reply_text("User pas trouvé, il doit d'abord faire /start")
    except: pass

async def send_market_analysis(context: ContextTypes.DEFAULT_TYPE, chat_id: int, forced=False):
    try:
        r = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=15&page=1&price_change_percentage=24h", timeout=15).json()
        top = sorted(r, key=lambda x: abs(x.get('price_change_percentage_24h',0) or 0), reverse=True)[:3]
        msg = "🚨 ALERTE AUTO JOSH AI 🚨\n\n"
        for coin in top:
            name = coin['symbol'].upper()
            price = coin['current_price']
            change = coin.get('price_change_percentage_24h',0)
            side = "ACHAT 📈" if change>0 else "VENTE 📉"
            tp1 = price*1.02; tp2 = price*1.05; sl1 = price*0.985; sl2 = price*0.97
            if change<0:
                tp1 = price*0.98; tp2 = price*0.95; sl1 = price*1.015; sl2 = price*1.03
            msg += f"🔥 {name} {price:.2f}$ ({change:.2f}%)\n{side}\nTP1: {tp1:.2f}$ TP2: {tp2:.2f}$\nSL1: {sl1:.2f}$ SL2: {sl2:.2f}$\n\n"
        await context.bot.send_message(chat_id=chat_id, text=msg)
    except Exception as e:
        print(f"Erreur: {e}")

# JOB PAYANT: toutes les 3h
async def auto_alert_paid(context: ContextTypes.DEFAULT_TYPE):
    print(f"[{datetime.now()}] Alerte PAYANT 3h")
    for uid, data in list(users_db.items()):
        if data.get("tier")=="paid" and not data.get("blocked") and data.get("chat_id"):
            await send_market_analysis(context, data["chat_id"])
            await asyncio.sleep(1)

# JOB GRATUIT: 1 fois par jour
async def auto_alert_free(context: ContextTypes.DEFAULT_TYPE):
    print(f"[{datetime.now()}] Alerte GRATUIT 1/jour")
    for uid, data in list(users_db.items()):
        if data.get("tier")=="free" and not data.get("blocked") and data.get("chat_id"):
            await send_market_analysis(context, data["chat_id"])
            await asyncio.sleep(1)

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyse", lambda u,c: send_market_analysis(c, u.effective_chat.id)))
    app.add_handler(CommandHandler("solde", solde))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("addpaid", addpaid))

    # PAYANT toutes les 3h = 10800 sec, premier envoi 30 sec après démarrage
    app.job_queue.run_repeating(auto_alert_paid, interval=10800, first=30)
    # GRATUIT toutes les 24h = 86400 sec, premier envoi 60 sec après démarrage
    app.job_queue.run_repeating(auto_alert_free, interval=86400, first=60)

    print("JOSH AI V6.1 PAYANT/GRATUIT LANCÉ")
    app.run_polling()
