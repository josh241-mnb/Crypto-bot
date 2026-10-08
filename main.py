import os, logging, requests, asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_ADMIN_ID = 8348716806 # <-- TON ID Derrick, seul toi peux faire /addpaid
logging.basicConfig(level=logging.INFO)

users_db = {}

def get_user(uid, chat_id=None):
    if uid not in users_db:
        users_db[uid] = {"lang":"fr","wins":0,"dette":0.0,"blocked":False,"chat_id": chat_id, "tier":"free"}
    if chat_id:
        users_db[uid]["chat_id"]=chat_id
    return users_db[uid]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id, update.effective_chat.id)
    tier = "GRATUIT (1/jour)" if u["tier"]=="free" else "PAYANT (toutes les 3h) 🔥"
    await update.message.reply_text(f"Salut {update.effective_user.first_name} 👋 JOSH AI V6.2\nStatut: {tier}\n\n/analyse - scan\n/solde - dette\n/myid - ton ID\n/pay - devenir payant")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ton ID est: `{update.effective_user.id}`\nEnvoie-le au patron.", parse_mode="Markdown")

async def solde(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    await update.message.reply_text(f"Tier: {u['tier']}\nWins: {u['wins']} Dette: {u['dette']}$/7.5$")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 PAYANT: 20$/mois ou 80$/an\nContacte @Josh_mnb et envoie /myid pour activation.")

async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID:
        await update.message.reply_text("Pas autorisé.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addpaid ID_CLIENT")
        return
    try:
        tid = int(context.args[0])
        if tid in users_db:
            users_db[tid]["tier"]="paid"
            users_db[tid]["blocked"]=False
            users_db[tid]["dette"]=0
            await update.message.reply_text(f"User {tid} -> PAYANT ✅")
            await context.bot.send_message(chat_id=users_db[tid]["chat_id"], text="🎉 Tu es PASSÉ PAYANT! Alertes toutes les 3h activées 🔥")
        else:
            await update.message.reply_text("User pas encore /start sur le bot.")
    except Exception as e:
        await update.message.reply_text(f"Erreur: {e}")

async def send_market_analysis(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        r = requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=15&page=1&price_change_percentage=24h", timeout=15).json()
        top = sorted(r, key=lambda x: abs(x.get('price_change_percentage_24h',0) or 0), reverse=True)[:3]
        msg = "🚨 ALERTE AUTO JOSH AI V6.2 🚨\n\n"
        for c in top:
            name = c['symbol'].upper()
            price = c['current_price']
            ch = c.get('price_change_percentage_24h',0)
            side = "ACHAT 📈" if ch>0 else "VENTE 📉"
            tp1 = price*1.02 if ch>0 else price*0.98
            tp2 = price*1.05 if ch>0 else price*0.95
            sl1 = price*0.985 if ch>0 else price*1.015
            sl2 = price*0.97 if ch>0 else price*1.03
            msg += f"🔥 {name} {price:.2f}$ ({ch:.2f}%)\n{side}\nTP1 {tp1:.2f}$ TP2 {tp2:.2f}$\nSL1 {sl1:.2f}$ SL2 {sl2:.2f}$\n\n"
        await context.bot.send_message(chat_id=chat_id, text=msg)
    except Exception as e:
        print(e)

async def job_paid(context: ContextTypes.DEFAULT_TYPE):
    for uid, data in list(users_db.items()):
        if data.get("tier")=="paid" and not data.get("blocked") and data.get("chat_id"):
            await send_market_analysis(context, data["chat_id"])
            await asyncio.sleep(1)

async def job_free(context: ContextTypes.DEFAULT_TYPE):
    for uid, data in list(users_db.items()):
        if data.get("tier")=="free" and not data.get("blocked") and data.get("chat_id"):
            await send_market_analysis(context, data["chat_id"])
            await asyncio.sleep(1)

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("solde", solde))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("addpaid", addpaid))
    app.add_handler(CommandHandler("analyse", lambda u,c: send_market_analysis(c, u.effective_chat.id)))

    app.job_queue.run_repeating(job_paid, interval=10800, first=30) # 3h
    app.job_queue.run_repeating(job_free, interval=86400, first=60) # 24h

    print("JOSH AI V6.2 LANCE")
    app.run_polling()
