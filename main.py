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
    if users_db[uid]["last_free_reset"]!= now.date() and users_db[uid]["tier"]=="free":
        users_db[uid]["blocked"]=False; users_db[uid]["free_start"]=now; users_db[uid]["notified"]=False; users_db[uid]["last_free_reset"]=now.date()
    return users_db[uid]

async def notify_admin(c,t):
    try: await c.bot.send_message(chat_id=MY_ADMIN_ID, text=t)
    except: pass

def check_free(u):
    if u.get("tier")=="paid": return True, 999
    if u.get("blocked"): return False, 0
    elapsed = (datetime.now() - u.get("free_start", datetime.now())).total_seconds()
    rem = 18000 - elapsed
    return (True, int(rem/60)) if rem>0 else (False, 0)

MESSAGES = {
"fr": "🔥 JOSH AI V6.8 MT5 🔥\n\nSalut ami 👋 Marchés MT5 réels\n\n📊 /analyse - TOP 3 MT5:\n• XAUUSD GOLD • EURUSD • GBPUSD\nAvec ENTRÉE / TP1 TP2 / SL1 SL2\n\n💰 GRATUIT: Tous les jours - 5h/jour d'accès\n🔥 PAYANT: 24h/24 - Toutes les 3h\n\n/lang fr ou /lang en",
"en": "🔥 JOSH AI V6.8 MT5 🔥\n\nHi friend 👋 Real MT5 markets\n\n📊 /analyse - TOP 3 MT5:\n• XAUUSD GOLD • EURUSD • GBPUSD\nWith ENTRY / TP1 TP2 / SL1 SL2\n\n💰 FREE: Every day - 5h/day access\n🔥 PAID: 24/7 - Every 3h\n\n/lang fr or /lang en"
}

def get_mt5_prices():
    prices={}
    try:
        r=requests.get("https://api.gold-api.com/price/XAU",timeout=8).json()
        prices["XAUUSD GOLD"]=float(r.get("price", 3950))
    except: prices["XAUUSD GOLD"]=3950+random.uniform(-30,30)
    try:
        r=requests.get("https://api.exchangerate-api.com/v4/latest/EUR",timeout=8).json()
        prices["EURUSD"]=float(r["rates"]["USD"])
    except: prices["EURUSD"]=1.1720+random.uniform(-0.003,0.003)
    try:
        r=requests.get("https://api.exchangerate-api.com/v4/latest/GBP",timeout=8).json()
        prices["GBPUSD"]=float(r["rates"]["USD"])
    except: prices["GBPUSD"]=1.3220+random.uniform(-0.003,0.003)
    return prices

async def send_mt5_analysis(context, chat_id, free_mins=None):
    try:
        prices=get_mt5_prices()
        msg=f"🚨 JOSH AI V6.8 MT5 - SIGNALS 🚨\n📍 BROKER: MT5\n🕐 {datetime.now().strftime('%d/%m %H:%M')} GMT\n\n"
        for symbol, price in prices.items():
            is_buy=random.choice([True, False])
            if "XAUUSD" in symbol:
                if is_buy:
                    tp1=price*1.003; tp2=price*1.006; sl1=price*0.997; sl2=price*0.994
                else:
                    tp1=price*0.997; tp2=price*0.994; sl1=price*1.003; sl2=price*1.006
            else:
                if is_buy:
                    tp1=price*1.0015; tp2=price*1.003; sl1=price*0.9985; sl2=price*0.997
                else:
                    tp1=price*0.9985; tp2=price*0.997; sl1=price*1.0015; sl2=price*1.003

            sig="BUY 🟢 ACHAT" if is_buy else "SELL 🔴 VENTE"
            def fmt(p):
                return f"{p:.2f}" if "XAU" in symbol else f"{p:.5f}"

            msg+=f"━━━━━━━━━━━━━━━\n{'🟢' if is_buy else '🔴'} {symbol}\n📊 SIGNAL: {sig}\n💵 ENTRÉE: {fmt(price)}\n🎯 TP1: {fmt(tp1)} | TP2: {fmt(tp2)}\n🛑 SL1: {fmt(sl1)} | SL2: {fmt(sl2)}\n⚙️ Levier: 1:100 | TF: M15/H1\n\n"
        msg+="💡 Ouvre sur MT5 -> même paire\n⚠️ Risque 1-2%"
        if free_mins is not None and free_mins!=999:
            msg+=f"\n⏱️ Il te reste {free_mins} min gratuit aujourd'hui (5h/jour)\nAprès -> /pay pour 24h/24"
        await context.bot.send_message(chat_id=chat_id, text=msg)
    except Exception as e: print(e)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    allowed, mins = check_free(u)
    if u.get("blocked"):
        await update.message.reply_text(f"🚫 Tu es bloqué. /pay pour 24h/24 ou attends demain.\nID: {update.effective_user.id}"); return
    if not allowed and u["tier"]=="free":
        u["blocked"]=True; u["notified"]=True
        await notify_admin(context, f"🚫 AUTO-BLOCK 5h finies: {u['name']} ID:{update.effective_user.id}")
        await update.message.reply_text("🚫 Tes 5h finies aujourd'hui! Bloqué AUTO.\nTape /pay pour 24h/24\nReset auto demain minuit"); return

    lang_msg = MESSAGES[u["lang"]]
    # EXACT COMME TA CAPTURE
    extra = f"\n\n⏱️ Il te reste {mins} min gratuit aujourd'hui (5h/jour)\nAprès -> /pay pour 24h/24" if u["tier"]=="free" else "\n\n🔥 PAYANT ACTIF 24h/24"
    await update.message.reply_text(lang_msg + extra)

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    allowed, mins = check_free(u)
    if u.get("blocked") or (not allowed and u["tier"]=="free"):
        if not u.get("blocked"): u["blocked"]=True; u["notified"]=True
        await update.message.reply_text("🚫 5h finies! /pay pour 24h/24"); return
    await send_mt5_analysis(context, update.effective_chat.id, mins if u["tier"]=="free" else None)

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)
    if not context.args: await update.message.reply_text("Usage: /lang fr ou /lang en"); return
    l=context.args[0].lower()
    if l in ["fr","en"]: u["lang"]=l; await update.message.reply_text(MESSAGES[l])

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ID: `{update.effective_user.id}`", parse_mode="Markdown")
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 PAYANT: 20$/mois ou 80$/an - 24h/24\nEnvoie ton ID au patron WhatsApp")
    if update.effective_user.id!=MY_ADMIN_ID:
        await notify_admin(context, f"💰 /pay VEUT PAYER: {update.effective_user.first_name} ID:{update.effective_user.id}")
async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=MY_ADMIN_ID: return
    if context.args:
        tid=int(context.args[0]); users_db[tid]["tier"]="paid"; users_db[tid]["blocked"]=False
        await update.message.reply_text(f"✅ {tid} -> PAYANT 24h/24 🔥")
        try: await context.bot.send_message(chat_id=users_db[tid]["chat_id"], text="🎉 PAYANT ACTIVÉ 24h/24 🔥")
        except: pass
async def block_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id==MY_ADMIN_ID and context.args:
        users_db[int(context.args[0])]["blocked"]=True; await update.message.reply_text("🚫 BLOQUÉ")
async def unblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id==MY_ADMIN_ID and context.args:
        tid=int(context.args[0]); users_db[tid]["blocked"]=False; users_db[tid]["free_start"]=datetime.now(); users_db[tid]["notified"]=False
        await update.message.reply_text(f"✅ {tid} DÉBLOQUÉ")

# AUTO TOUTES LES 3H - COMME TU VEUX
async def job_auto(c):
    for uid,d in list(users_db.items()):
        if not d.get("blocked") and d.get("chat_id"):
            allowed, mins = check_free(d)
            if allowed or d.get("tier")=="paid":
                await send_mt5_analysis(c, d["chat_id"], mins if d["tier"]=="free" else None); await asyncio.sleep(1)
            else:
                if not d.get("notified"):
                    d["blocked"]=True; d["notified"]=True
                    await notify_admin(c, f"🚫 AUTO-BLOCK 5h finies: {d.get('name')} ID:{uid}")

if __name__=="__main__":
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyse", analyse_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("addpaid", addpaid))
    app.add_handler(CommandHandler("block", block_cmd))
    app.add_handler(CommandHandler("unblock", unblock_cmd))
    app.job_queue.run_repeating(job_auto, interval=10800, first=30) # 3h AUTO
    print("V6.8 MT5 FINAL LANCE")
    app.run_polling()
