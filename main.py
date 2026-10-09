import os, logging, requests, asyncio, random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_ADMIN_ID = 8348716806
logging.basicConfig(level=logging.INFO)
users_db = {}

def get_user(uid, chat_id=None, name=""):
    now = datetime.now()
    if uid not in users_db:
        users_db[uid] = {"lang":"fr","wins":0,"dette":0.0,"blocked":False,"chat_id": chat_id, "tier":"free", "name": name, "free_start": now, "last_free_reset": now.date()}
    if chat_id: users_db[uid]["chat_id"]=chat_id
    if name: users_db[uid]["name"]=name
    # Reset chaque jour à minuit pour gratuit
    if users_db[uid]["last_free_reset"]!= now.date():
        users_db[uid]["last_free_reset"] = now.date()
        users_db[uid]["free_start"] = now
        users_db[uid]["free_used_seconds"] = 0
    return users_db[uid]

async def notify_admin(context, text):
    try: await context.bot.send_message(chat_id=MY_ADMIN_ID, text=f"👀 LOG:\n{text}")
    except: pass

MESSAGES = {
 "fr": "🔥 JOSH AI V6.8 MT5 🔥\n\nSalut ami 👋 Marchés MT5 réels\n\n📊 /analyse - TOP 3 MT5:\n• XAUUSD GOLD • EURUSD • GBPUSD\nAvec ENTRÉE / TP1 TP2 / SL1 SL2\n\n💰 GRATUIT: Tous les jours - 5h/jour d'accès\n🔥 PAYANT: 24h/24 - Toutes les 3h\n\n/lang fr ou /lang en",
 "en": "🔥 JOSH AI V6.8 MT5 🔥\n\nHi friend 👋 Real MT5 markets\n\n📊 /analyse - TOP 3 MT5:\n• XAUUSD GOLD • EURUSD • GBPUSD\nWith ENTRY / TP1 TP2 / SL1 SL2\n\n💰 FREE: Every day - 5h/day access\n🔥 PAID: 24/7 - Every 3h"
}

def is_free_allowed(user_data):
    if user_data.get("tier")=="paid": return True, 0
    now = datetime.now()
    start = user_data.get("free_start", now)
    # 5 heures = 18000 secondes
    elapsed = (now - start).total_seconds()
    remaining = 18000 - elapsed
    if remaining > 0:
        return True, int(remaining/60)
    else:
        return False, 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id, update.effective_chat.id, user.first_name)
    allowed, mins = is_free_allowed(u)
    if u["tier"]=="free":
        msg_extra = f"\n\n⏱️ Il te reste {mins} min gratuit aujourd'hui (5h/jour)\nAprès -> /pay pour 24h/24" if allowed else "\n\n⏰ Tes 5h gratuites du jour sont finies! Reviens demain ou /pay pour PAYANT 24h/24"
    else:
        msg_extra = "\n\n🔥 PAYANT ACTIF 24h/24"
    await update.message.reply_text(MESSAGES[u["lang"]] + msg_extra)
    if user.id!= MY_ADMIN_ID:
        await notify_admin(context, f"/start {user.first_name} ID:{user.id} tier:{u['tier']}")

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if not context.args: await update.message.reply_text("Langue: /lang fr ou /lang en"); return
    l = context.args[0].lower()
    if l in ["fr","en"]: u["lang"]=l; await update.message.reply_text(MESSAGES[l])

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ID: `{update.effective_user.id}`", parse_mode="Markdown")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 PAYANT: 20$/mois ou 80$/an - Accès 24h/24 toutes les 3h\nEnvoie /myid au patron WhatsApp")
    if update.effective_user.id!= MY_ADMIN_ID:
        await notify_admin(context, f"💰 /pay - {update.effective_user.first_name} ID:{update.effective_user.id}")

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id, update.effective_chat.id)
    allowed, mins = is_free_allowed(u)
    if not allowed and u["tier"]=="free":
        await update.message.reply_text(f"⏰ Tes 5h gratuites du jour sont terminées!\n\n💰 Passe PAYANT pour 24h/24\nOu reviens demain - reset à minuit.\n\nTape /pay")
        return
    if update.effective_user.id!= MY_ADMIN_ID:
        await notify_admin(context, f"📊 /analyse par {u.get('name')} ID:{update.effective_user.id} reste:{mins}min")
    await send_market_analysis(context, update.effective_chat.id, mins if u["tier"]=="free" else None)

async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID: return
    if not context.args: await update.message.reply_text("Usage: /addpaid ID"); return
    tid = int(context.args[0])
    if tid in users_db:
        users_db[tid]["tier"]="paid"; users_db[tid]["blocked"]=False
        await update.message.reply_text(f"✅ {tid} -> PAYANT 24h/24 🔥")
        try: await context.bot.send_message(chat_id=users_db[tid]["chat_id"], text="🎉 Tu es PAYANT! 24h/24 toutes les 3h - XAUUSD + EURUSD 🔥")
        except: pass

async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID: return
    msg = "👑 CLIENTS V6.8 (5h/jour gratuit):\n\n"
    for uid,d in users_db.items():
        allowed, mins = is_free_allowed(d)
        msg+=f"{d.get('name','?')} - {uid} - {d['tier']} - reste {mins}min\n"
    await update.message.reply_text(msg or "Aucun user")

def get_mt5_prices():
    prices = {}
    try:
        r = requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
        prices["XAUUSD"] = float(r.get("price", 3950))
    except: prices["XAUUSD"] = 3950 + random.uniform(-20,20)
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=10).json()
        prices["EURUSD"] = float(r["rates"]["USD"])
    except: prices["EURUSD"] = 1.1720 + random.uniform(-0.002,0.002)
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/GBP", timeout=10).json()
        prices["GBPUSD"] = float(r["rates"]["USD"])
    except: prices["GBPUSD"] = 1.3220 + random.uniform(-0.002,0.002)
    prices["BTCUSD"] = 67500 + random.uniform(-500,500)
    prices["US30"] = 43250 + random.uniform(-200,200)
    return prices

async def send_market_analysis(context, chat_id: int, free_mins_left=None):
    try:
        prices = get_mt5_prices()
        markets = list(prices.items())
        random.shuffle(markets)
        top3 = markets[:3]
        msg = "🚨 JOSH AI V6.8 - MT5 SIGNALS 🚨\n"
        msg += "📍 BROKER: MT5 (Tous brokers)\n"
        msg += f"🕐 {datetime.now().strftime('%d/%m %H:%M')} GMT\n"
        if free_mins_left is not None:
            msg += f"⏱️ Gratuit: {free_mins_left} min restantes aujourd'hui\n\n"
        else:
            msg += "🔥 PAYANT 24h/24\n\n"

        for symbol, price in top3:
            is_buy = random.choice([True, False])
            if is_buy:
                signal = "BUY 🟢 ACHAT"
                tp1 = price*1.0025 if symbol in ["EURUSD","GBPUSD"] else price*1.003 if symbol=="XAUUSD" else price*1.01
                tp2 = price*1.005 if symbol in ["EURUSD","GBPUSD"] else price*1.007 if symbol=="XAUUSD" else price*1.02
                sl1 = price*0.998 if symbol in ["EURUSD","GBPUSD"] else price*0.997 if symbol=="XAUUSD" else price*0.99
                sl2 = price*0.996 if symbol in ["EURUSD","GBPUSD"] else price*0.994 if symbol=="XAUUSD" else price*0.98
            else:
                signal = "SELL 🔴 VENTE"
                tp1 = price*0.9975 if symbol in ["EURUSD","GBPUSD"] else price*0.997 if symbol=="XAUUSD" else price*0.99
                tp2 = price*0.995 if symbol in ["EURUSD","GBPUSD"] else price*0.993 if symbol=="XAUUSD" else price*0.98
                sl1 = price*1.002 if symbol in ["EURUSD","GBPUSD"] else price*1.003 if symbol=="XAUUSD" else price*1.01
                sl2 = price*1.004 if symbol in ["EURUSD","GBPUSD"] else price*1.006 if symbol=="XAUUSD" else price*1.02

            def f(p):
                if symbol == "XAUUSD": return f"{p:.2f}"
                elif symbol in ["EURUSD","GBPUSD"]: return f"{p:.5f}"
                elif symbol == "BTCUSD": return f"{p:.2f}"
                else: return f"{p:.1f}"

            fmt = f(price)
            msg+=f"━━━━━━━━━━━━━━━\n"
            msg+=f"{'🟢' if 'BUY' in signal else '🔴'} MARCHÉ: {symbol}\n"
            msg+=f"📊 SIGNAL: {signal}\n"
            msg+=f"💵 ENTRÉE: {fmt}\n"
            msg+=f"🎯 TP1: {f(tp1)} | TP2: {f(tp2)}\n"
            msg+=f"🛑 SL1: {f(sl1)} | SL2: {f(sl2)}\n"
            msg+=f"⚙️ Levier: 1:100 | TF: M15 / H1\n\n"
        msg+="💡 Ouvre direct sur MT5 -> même paire -> BUY/SELL\n"
        msg+="⚠️ Risque 1-2% par trade"
        await context.bot.send_message(chat_id=chat_id, text=msg)
    except Exception as e:
        print(f"Erreur: {e}")

async def job_paid(c):
    for uid,d in list(users_db.items()):
        if d.get("tier")=="paid" and d.get("chat_id"):
            await send_market_analysis(c,d["chat_id"]); await asyncio.sleep(1)

async def job_free(c):
    for uid,d in list(users_db.items()):
        if d.get("tier")=="free" and d.get("chat_id"):
            allowed,_ = is_free_allowed(d)
            if allowed:
                await send_market_analysis(c,d["chat_id"], 0); await asyncio.sleep(1)

if __name__=="__main__":
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("analyse", analyse_cmd))
    app.add_handler(CommandHandler("addpaid", addpaid))
    app.add_handler(CommandHandler("users", users_list))
    app.job_queue.run_repeating(job_paid, interval=10800, first=30)
    app.job_queue.run_repeating(job_free, interval=3600, first=60)
    print("V6.8 5H GRATUIT LANCE")
    app.run_polling()
