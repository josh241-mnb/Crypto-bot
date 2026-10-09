import os, logging, requests, random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_ADMIN_ID = 8348716806
logging.basicConfig(level=logging.INFO)
users_db = {}

def get_user(uid, chat_id=None, name=""):
    now = datetime.now()
    if uid not in users_db:
        users_db[uid] = {"lang":"fr","blocked":False,"chat_id":chat_id,"tier":"free","name":name,"free_start":now,"last_free_reset":now.date(),"wins":0,"losses":0,"debt":0.0,"debt_block":False,"last_prices":{},"sr_symbol":"GOLD"}
    if chat_id: users_db[uid]["chat_id"]=chat_id
    if name: users_db[uid]["name"]=name
    if users_db[uid]["last_free_reset"]!=now.date() and users_db[uid]["tier"]=="free" and not users_db[uid].get("debt_block"):
        users_db[uid]["blocked"]=False; users_db[uid]["free_start"]=now; users_db[uid]["last_free_reset"]=now.date()
    return users_db[uid]

async def notify_admin(c,t):
    try: await c.bot.send_message(chat_id=MY_ADMIN_ID, text=t)
    except: pass

def check_free(u):
    if u.get("debt_block"): return False, 0
    if u.get("tier")=="paid": return True, 999
    if u.get("blocked"): return False, 0
    rem = 18000 - (datetime.now() - u.get("free_start", datetime.now())).total_seconds()
    return (True, int(rem/60)) if rem>0 else (False, 0)

def get_mt5_prices():
    p={}
    try: r=requests.get("https://api.gold-api.com/price/XAU",timeout=5).json(); p["GOLD"]=float(r.get("price", 4191))
    except: p["GOLD"]=4191.00
    p["EURUSD"]=1.12000; p["GBPUSD"]=1.32000
    return p

async def send_lang_choice(chat_id, context):
    kb = [[InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"), InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"), InlineKeyboardButton("🇨🇫 Sango", callback_data="lang_sg")]]
    await context.bot.send_message(chat_id=chat_id, text="🌍 Choisis ta langue / Choose language / Ti lege ti molengue:", reply_markup=InlineKeyboardMarkup(kb))

async def send_top_markets(context, chat_id, user_prices, free_mins=None, lang="fr"):
    if lang=="en":
        msg = f"🔥 JOSH AI V6 - TOP MT5 MARKETS 🔥\nMT5 Real | {datetime.now().strftime('%d/%m %H:%M')} GMT\n\nHere are 3 good markets to trade now:\n\n"
        for sym, price in user_prices.items():
            fmt = f"{price:.2f}" if sym=="GOLD" else f"{price:.5f}"
            msg += f"🔹 {sym}\nPrice: {fmt} | Trend: BEARISH 🔴\nScore: 91%\n\n"
        msg += f"Which one? Type: gold / eurusd / gbpusd or 1/2/3"
    else:
        msg = f"🔥 JOSH AI V6 - TOP MARCHES MT5 🔥\nMT5 Réel | {datetime.now().strftime('%d/%m %H:%M')} GMT\n\nVoici les 3 bons marchés où tu peux trader maintenant:\n\n"
        for sym, price in user_prices.items():
            fmt = f"{price:.2f}" if sym=="GOLD" else f"{price:.5f}"
            msg += f"🔹 {sym}\nPrix: {fmt} | Tendance: BAISSIER 🔴\nScore: 91%\n\n"
        msg += f"Lequel veux-tu trader?\nTape: gold ou eurusd ou gbpusd\nOu tape 1 / 2 / 3\n"
    if free_mins and free_mins!=999:
        msg += f"\n⏱️ Reste {free_mins} min gratuit"
    kb = [[InlineKeyboardButton("🥇 GOLD", callback_data="GOLD"), InlineKeyboardButton("💶 EURUSD", callback_data="EURUSD"), InlineKeyboardButton("💷 GBPUSD", callback_data="GBPUSD")]]
    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=InlineKeyboardMarkup(kb))

async def send_detailed_analysis(context, chat_id, symbol_key, price, lang="fr"):
    is_gold = symbol_key=="GOLD"
    sup = price*0.997 if is_gold else price*0.998
    res = price*1.003 if is_gold else price*1.002
    entry = price; tp1 = price*0.99968; tp2 = price*0.9989; tp3 = price*0.995; sl1 = price*1.0058
    def fmt(p): return f"{p:.2f}" if is_gold else f"{p:.5f}"

    if lang=="en":
        txt = f"🔥 DETAILED: {symbol_key} 🔥\nMT5 / {datetime.now().strftime('%d/%m %H:%M')} GMT\n\n📊 SIGNAL: SELL 🔴\n💵 ENTRY: {fmt(entry)}\n🎯 TP1: {fmt(tp1)}\n🎯 TP2: {fmt(tp2)}\n🎯 TP3: {fmt(tp3)} (Runner)\n🛑 SL1: {fmt(sl1)}\n📍 SUPPORT: {fmt(sup)} 🔵\n📍 RESISTANCE: {fmt(res)} 🔴\n\n📈 STRATEGY:\nScalping EMA 50 + EMA 200\nWait H1 candle confirmation\nSecure 50% & let run\n\nOpen MT5 -> {symbol_key}"
    else:
        txt = f"🔥 ANALYSE DETAILLEE: {symbol_key} 🔥\nMT5 / {datetime.now().strftime('%d/%m %H:%M')} GMT\n\n📊 SIGNAL: SELL 🔴 VENTE\n💵 ENTREE: {fmt(entry)}\n🎯 TP1: {fmt(tp1)}\n🎯 TP2: {fmt(tp2)}\n🎯 TP3: {fmt(tp3)} (Runner)\n🛑 SL1: {fmt(sl1)}\n📍 SUPPORT: {fmt(sup)} 🔵\n📍 RESISTANCE: {fmt(res)} 🔴\n\n📈 STRATEGIE ADOPTEE:\nScalping EMA 50 + EMA 200\nAttends confirmation bougie H1\nTF M15 + TF H1 + TF M1 = 1100\nSécurise 50% & laisse courir TP2/TP3\nSécurité 50% & 1900\n\nOuvre MT5 -> {symbol_key}\nMets lot direct!"
    kb = [[InlineKeyboardButton("✅ WIN Gagné", callback_data="WIN"), InlineKeyboardButton("❌ LOSS Perdu", callback_data="LOSS")]]
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id, q.message.chat_id, q.from_user.first_name)
    d = q.data

    if d.startswith("lang_"):
        lang = d.split("_")[1]; u["lang"]=lang
        await notify_admin(context, f"🌍 {u['name']} langue {lang} ID:{q.from_user.id}")
        await q.message.reply_text(f"✅ Langue {lang} ok!")
        prices=get_mt5_prices(); u["last_prices"]=prices
        allowed, mins = check_free(u)
        await send_top_markets(context, q.message.chat_id, prices, mins, lang)
        return

    if d in ["GOLD","EURUSD","GBPUSD"]:
        price = u.get("last_prices",{}).get(d, 4191 if d=="GOLD" else 1.12)
        await notify_admin(context, f"👆 {u['name']} a cliqué {d} ID:{q.from_user.id} Bilan:{u['debt']}$")
        await send_detailed_analysis(context, q.message.chat_id, d, price, u.get("lang","fr"))
        return

    if d=="WIN":
        u["wins"]+=1; u["debt"]=round(u["debt"]+1.5,2)
        await q.message.reply_text(f"✅ Tu as gagné!\n\nMon bilan à payer: {u['debt']}$\n{u['wins']} WIN / {u['losses']} LOSS")
        await notify_admin(context, f"🔔 {u['name']} WIN ID:{q.from_user.id} DOIT: {u['debt']}$")
        if u["debt"]>=7.5:
            u["debt_block"]=True; u["blocked"]=True
            await notify_admin(context, f"🚨 BLOQUÉ 7,5$ {u['name']} ID:{q.from_user.id}")
            # MESSAGE ORIGINAL REMIS - JE NE RETIRE PLUS
            await context.bot.send_message(chat_id=q.message.chat_id, text=f"⛔ BOT ARRETE AUTOMATIQUEMENT ⛔\n\nMon bilan à payer: {u['debt']}$ ({u['wins']} WIN x 1,5$)\nTape /pay et envoie ton ID au patron pour payer mon BILAN\n\n🚫 BLOQUE BILAN 7.5$ (5 WIN x 1,5$)\n/pay + envoie ID au patron pour payer mon\nID: {q.from_user.id}\n\nMON BILAN PAYE! Bot débloqué! Tu peux refaire 0 WIN\n\nDommage mais ne pas abandonne!\nNe lâche pas, le prochain sera gagnant! 😊")
        return

    if d=="LOSS":
        u["losses"]+=1
        # MESSAGE DOMMAGE REMIS ICI - COMME AVANT
        await q.message.reply_text(f"❌ LOSS Perdu - courage!\n\nDommage mais ne pas abandonne!\nNe lâche pas, le prochain sera gagnant! 😊\n\nAh toi aussi tu as perdu? Courage ami!")
        await notify_admin(context, f"❌ {u['name']} LOSS ID:{q.from_user.id}")
        return

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    await notify_admin(context, f"🟢 NOUVEAU: {u['name']} a pris le bot! ID:{update.effective_user.id} @{update.effective_user.username}")
    await send_lang_choice(update.effective_chat.id, context)

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    if u.get("debt_block"): await update.message.reply_text(f"🚫 BLOQUE BILAN {u['debt']}$"); return
    allowed, mins = check_free(u)
    if not allowed: await update.message.reply_text("🚫 5h finies /pay"); return
    prices=get_mt5_prices(); u["last_prices"]=prices
    await send_top_markets(context, update.effective_chat.id, prices, mins, u.get("lang","fr"))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    txt = update.message.text.lower()
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)

    if any(x in txt for x in ["mois","an","payer","paye","dette","bilan"]):
        await notify_admin(context, f"💰 VEUT PAYER: {u['name']} ID:{update.effective_user.id} Veut:{txt} Doit:{u['debt']}$")
        await update.message.reply_text(f"✅ Reçu! ID {update.effective_user.id} envoyé au patron. Il va te débloquer.\n\nDommage mais ne pas abandonne! 😊"); return

    if "lang" in txt:
        await send_lang_choice(update.effective_chat.id, context); return

    target=None
    if any(x in txt for x in ["gold","xau","google","gole","gld","1","or"]): target="GOLD"
    elif any(x in txt for x in ["eur","euro","2"]): target="EURUSD"
    elif any(x in txt for x in ["gbp","bipy","bp","gbpusd","gu","3","livre"]): target="GBPUSD"
    if target:
        price = u.get("last_prices",{}).get(target) or get_mt5_prices().get(target)
        await notify_admin(context, f"📊 {u['name']} a tapé {target} ID:{update.effective_user.id} Bilan:{u['debt']}$")
        await send_detailed_analysis(context, update.effective_chat.id, target, price, u.get("lang","fr"))

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)
    await notify_admin(context, f"💰 /pay {u['name']} ID:{update.effective_user.id} {u['debt']}$")
    await update.message.reply_text(f"ID: {update.effective_user.id}\nBilan {u['debt']}$")

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_lang_choice(update.effective_chat.id, context)

async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=MY_ADMIN_ID: return
    tid=int(context.args[0]); plan=context.args[1].lower()
    if tid not in users_db: users_db[tid]=get_user(tid, tid, "Client")
    if plan=="dette": users_db[tid]["debt"]=0; users_db[tid]["debt_block"]=False; users_db[tid]["blocked"]=False; users_db[tid]["wins"]=0
    else:
        expire=datetime.now()+timedelta(days=30 if plan=="mois" else 365)
        users_db[tid]["tier"]="paid"; users_db[tid]["paid_until"]=expire; users_db[tid]["blocked"]=False; users_db[tid]["debt"]=0
    await update.message.reply_text(f"✅ {tid} {plan} OK")
    try: await context.bot.send_message(chat_id=users_db[tid]["chat_id"], text="🎉 PAYE! Débloqué!\n\nMON BILAN PAYE! Bot débloqué! Tu peux refaire 0 WIN")
    except: pass

if __name__=="__main__":
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyse", analyse_cmd))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("addpaid", addpaid))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("V6 FINAL COMPLET - RIEN RETIRE")
    app.run_polling()
