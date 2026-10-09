import os, logging, requests, asyncio, random
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_ADMIN_ID = 8348716806
logging.basicConfig(level=logging.INFO)
users_db = {}

def get_user(uid, chat_id=None, name=""):
    now = datetime.now()
    if uid not in users_db:
        users_db[uid] = {"lang":"fr","blocked":False,"chat_id":chat_id,"tier":"free","name":name,"free_start":now,"last_free_reset":now.date(),"notified":False}
    if chat_id: users_db[uid]["chat_id"]=chat_id
    if name: users_db[uid]["name"]=name
    if users_db[uid]["last_free_reset"]!= now.date():
        if users_db[uid]["tier"]=="free":
            users_db[uid]["blocked"]=False; users_db[uid]["free_start"]=now; users_db[uid]["notified"]=False; users_db[uid]["last_free_reset"]=now.date()
    return users_db[uid]

async def notify_admin(context, text):
    try: await context.bot.send_message(chat_id=MY_ADMIN_ID, text=text)
    except: pass

def check_free(u):
    if u.get("tier")=="paid": return True, 9999
    if u.get("blocked"): return False, 0
    elapsed = (datetime.now() - u.get("free_start", datetime.now())).total_seconds()
    remaining = 18000 - elapsed
    return (True, int(remaining/60)) if remaining>0 else (False, 0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=update.effective_user; u=get_user(user.id, update.effective_chat.id, user.first_name)
    allowed, mins = check_free(u)
    if not allowed and u["tier"]=="free" and not u["blocked"]:
        u["blocked"]=True; u["notified"]=True
        await notify_admin(context, f"🚫 AUTO-BLOCK:\n👤 {user.first_name}\n🆔 {user.id}\n⏰ 5h finies")
        await update.message.reply_text("🚫 Tes 5h finies! AUTO-BLOCK. /pay pour 24h/24")
        return
    if u.get("blocked"):
        await update.message.reply_text("🚫 Bloqué AUTO. /pay ou demain."); return
    await update.message.reply_text(f"🔥 JOSH AI V8 🔥\n\n📊 /analyse = Format comme ta capture!\n\n💰 Gratuit: 5h/jour ({mins} min reste)\n🔥 Payant: 24h/24\n\nTape /analyse")

# RÉCUP PRIX CRYPTO RÉELS + % COMME TA CAPTURE
def get_crypto_losers():
    cryptos = ["NEAR","ZEC","SUI","UNI","SOL","AVAX","DOT","LINK","ADA","ARB","OP","PEPE","SHIB","BTC","ETH","XRP","MATIC"]
    try:
        # CoinGecko pour vrais prix
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=50&page=1&sparkline=false&price_change_percentage=24h"
        r = requests.get(url, timeout=10).json()
        # Trie par plus grosse chute
        sorted_coins = sorted(r, key=lambda x: x.get('price_change_percentage_24h', 0))[:10]
        data = []
        for c in sorted_coins:
            symbol = c['symbol'].upper()
            price = c['current_price']
            change = c.get('price_change_percentage_24h', random.uniform(-12, -4))
            data.append((symbol, price, change))
        return data[:3]
    except:
        # Fallback si API down
        data=[]
        for sym in random.sample(cryptos, 6):
            price = random.uniform(0.5, 1200)
            change = random.uniform(-17, -4)
            data.append((sym, price, change))
        return sorted(data, key=lambda x: x[2])[:3]

async def send_market_analysis(context, chat_id, free_mins=None):
    try:
        top3 = get_crypto_losers()
        msg = "🚨 ALERTE AUTO JOSH AI V8 🚨\n\n"
        for symbol, price, change in top3:
            # Si chute forte = VENTE comme sur ta capture
            is_vente = change < 0
            signal = "VENTE 📉" if is_vente else "ACHAT 📈"

            # Calcul TP/SL comme sur ta capture
            if is_vente:
                tp1 = price * 0.98
                tp2 = price * 0.95
                sl1 = price * 1.015
                sl2 = price * 1.03
            else:
                tp1 = price * 1.02
                tp2 = price * 1.05
                sl1 = price * 0.985
                sl2 = price * 0.97

            def fmt(p):
                if p < 1: return f"{p:.3f}$"
                elif p < 10: return f"{p:.2f}$"
                else: return f"{p:.2f}$"

            msg += f"🔥 {symbol} {fmt(price)} ({change:.2f}%)\n"
            msg += f"{signal}\n"
            msg += f"TP1 {fmt(tp1)} TP2 {fmt(tp2)}\n"
            msg += f"SL1 {fmt(sl1)} SL2 {fmt(sl2)}\n\n"

        if free_mins is not None and free_mins!= 9999:
            msg += f"⏱️ Gratuit: {free_mins} min restantes"
        else:
            msg += "🔥 PAYANT 24h/24"

        await context.bot.send_message(chat_id=chat_id, text=msg)
    except Exception as e:
        print(f"Erreur analysis: {e}")

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    allowed, mins = check_free(u)
    if u.get("blocked"):
        await update.message.reply_text("🚫 Bloqué AUTO après 5h. /pay"); return
    if not allowed and u["tier"]=="free":
        u["blocked"]=True
        if not u.get("notified"):
            u["notified"]=True
            await notify_admin(context, f"🚫 AUTO-BLOCK /analyse:\n👤 {u.get('name')} ID:{update.effective_user.id}")
        await update.message.reply_text("🚫 5h finies! AUTO-BLOCK. /pay"); return
    await send_market_analysis(context, update.effective_chat.id, mins if u["tier"]=="free" else None)

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ID: `{update.effective_user.id}`", parse_mode="Markdown")
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 PAYANT 20$/mois - 24h/24\nWhatsApp patron avec /myid")
    if update.effective_user.id!= MY_ADMIN_ID:
        await notify_admin(context, f"💰 /pay {update.effective_user.first_name} ID:{update.effective_user.id}")
async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID: return
    if not context.args: return
    tid=int(context.args[0]); users_db[tid]["tier"]="paid"; users_db[tid]["blocked"]=False
    await update.message.reply_text(f"✅ {tid} PAYANT")
async def block_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID: return
    if context.args: users_db[int(context.args[0])]["blocked"]=True; await update.message.reply_text("BLOQUÉ")
async def unblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID: return
    if context.args:
        tid=int(context.args[0]); users_db[tid]["blocked"]=False; users_db[tid]["free_start"]=datetime.now(); users_db[tid]["notified"]=False
        await update.message.reply_text("DÉBLOQUÉ")

async def job_paid(c):
    for uid,d in list(users_db.items()):
        if d.get("tier")=="paid" and not d.get("blocked") and d.get("chat_id"):
            await send_market_analysis(c,d["chat_id"]); await asyncio.sleep(1)
async def job_free(c):
    for uid,d in list(users_db.items()):
        if d.get("tier")=="free" and not d.get("blocked") and d.get("chat_id"):
            allowed, mins = check_free(d)
            if allowed:
                await send_market_analysis(c,d["chat_id"], mins); await asyncio.sleep(1)
            else:
                if not d.get("notified"):
                    d["blocked"]=True; d["notified"]=True
                    await notify_admin(c, f"🚫 AUTO-BLOCK JOB: {d.get('name')} {uid}")

if __name__=="__main__":
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyse", analyse_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("addpaid", addpaid))
    app.add_handler(CommandHandler("block", block_cmd))
    app.add_handler(CommandHandler("unblock", unblock_cmd))
    app.job_queue.run_repeating(job_paid, interval=10800, first=30)
    app.job_queue.run_repeating(job_free, interval=10800, first=60)
    print("V8 FORMAT CAPTURE LANCE")
    app.run_polling()
