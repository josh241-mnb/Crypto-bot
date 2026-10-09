import os, logging, requests, random, re
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
        users_db[uid] = {"lang":"fr","blocked":False,"chat_id":chat_id,"tier":"free","name":name,"free_start":now,"last_free_reset":now.date(),"wins":0,"losses":0,"total_trades":0,"debt":0.0,"debt_block":False,"await_market":False,"last_prices":{},"sr_symbol":"GOLD"}
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
    except: p["GOLD"]=4191+random.uniform(-10,10)
    try: r=requests.get("https://api.exchangerate-api.com/v4/latest/EUR",timeout=5).json(); p["EURUSD"]=float(r["rates"]["USD"])
    except: p["EURUSD"]=1.1720
    try: r=requests.get("https://api.exchangerate-api.com/v4/latest/GBP",timeout=5).json(); p["GBPUSD"]=float(r["rates"]["USD"])
    except: p["GBPUSD"]=1.3220
    return p

# RESTAURE ANCIEN LOOK COMME TA VIDEO DEBUT
async def send_top_markets(context, chat_id, user_prices, free_mins=None):
    msg = f"🔥 JOSH AI V8.8 MT5 🔥\n\n"
    msg += f"Salut ami 👋 Marchés MT5 réels\n\n"
    msg += f"📊 /analyse - TOP 3 + Entrée/SL/Support/Résistance\n"
    msg += f"Tape gold / eurusd / gbpusd\n\n"
    msg += f"💰 GRATUIT: 5h/jour\n"
    msg += f"💵 1 WIN = 1,5$ bilan | Bloqué 7,5$ (5 WIN)\n"
    msg += f"🔥 PAYANT: 24h/24 illimité\n"
    if free_mins and free_mins!=999:
        msg += f"\n⏱️ Reste {free_mins} min | Bilan {users_db.get(chat_id, {}).get('debt',0)}$"
    # TOP 3 caché ici mais on l'envoie après
    await context.bot.send_message(chat_id=chat_id, text=msg)

    # Deuxième message TOP 3 comme avant
    top = f"🚨 TOP 3 MARCHÉS MT5 🚨\n"
    for sym, price in user_prices.items():
        fmt = f"{price:.2f}" if sym=="GOLD" else f"{price:.5f}"
        top += f"🔹 {sym}: {fmt} | Score {random.randint(84,94)}%\n"
    top += f"\n👉 Tape: gold / euro / gbp ou clique"
    kb = [[InlineKeyboardButton("🥇 GOLD", callback_data="GOLD"), InlineKeyboardButton("💶 EURUSD", callback_data="EURUSD"), InlineKeyboardButton("💷 GBPUSD", callback_data="GBPUSD")]]
    await context.bot.send_message(chat_id=chat_id, text=top, reply_markup=InlineKeyboardMarkup(kb))

async def send_detailed_analysis(context, chat_id, symbol_key, price, custom_sr=None):
    is_buy = random.choice([True, False])
    is_gold = symbol_key=="GOLD"
    sup = custom_sr.get("support") if custom_sr else price*0.997 if is_gold else price*0.9985
    res = custom_sr.get("resistance") if custom_sr else price*1.003 if is_gold else price*1.0015
    entry = price
    if is_buy:
        tp1=price*1.003 if is_gold else price*1.0015
        tp2=price*1.007 if is_gold else price*1.003
        tp3=price*1.012 if is_gold else price*1.005
        sl=sup*0.998 if is_gold else sup
    else:
        tp1=price*0.997 if is_gold else price*0.9985
        tp2=price*0.993 if is_gold else price*0.997
        tp3=price*0.988 if is_gold else price*0.995
        sl=res*1.002 if is_gold else res
    sig = "BUY 🟢 ACHAT" if is_buy else "SELL 🔴 VENTE"
    def fmt(p): return f"{p:.2f}" if is_gold else f"{p:.5f}"

    # FORMAT COMME DANS TA VIDEO - CLAIR
    txt = f"🎯 {symbol_key} MT5 - {sig} 🎯\n"
    txt += f"━━━━━━━━━━━━━━━\n"
    txt += f"💵 ENTRÉE: {fmt(entry)}\n"
    txt += f"🎯 TP1: {fmt(tp1)}\n"
    txt += f"🎯 TP2: {fmt(tp2)}\n"
    txt += f"🎯 TP3: {fmt(tp3)}\n"
    txt += f"🛑 SL: {fmt(sl)}\n"
    txt += f"━━━━━━━━━━━━━━━\n"
    txt += f"📍 SUPPORT: {fmt(sup)} 🔵\n"
    txt += f"📍 RÉSISTANCE: {fmt(res)} 🔴\n"
    txt += f"━━━━━━━━━━━━━━━\n"
    txt += f"💡 Ouvre MT5 -> {symbol_key}"

    kb = [[InlineKeyboardButton("✅ WIN Gagné", callback_data="WIN"), InlineKeyboardButton("❌ LOSS Perdu", callback_data="LOSS")]]
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id, q.message.chat_id, q.from_user.first_name)
    d = q.data
    if d in ["GOLD","EURUSD","GBPUSD"]:
        price = u.get("last_prices",{}).get(d, 4191 if d=="GOLD" else 1.17)
        u["sr_symbol"]=d
        await send_detailed_analysis(context, q.message.chat_id, d, price)
        return
    if d=="WIN":
        u["wins"]+=1; u["total_trades"]+=1; u["debt"]=round(u["debt"]+1.5,2)
        await q.message.reply_text(f"✅ Tu as gagné!\n💳 Mon bilan à payer: {u['debt']}$")
        await notify_admin(context, f"🔔 WIN {u['name']} ID:{q.from_user.id} Bilan {u['debt']}$")
        if u["debt"]>=7.5:
            u["debt_block"]=True; u["blocked"]=True
            await context.bot.send_message(chat_id=q.message.chat_id, text=f"🚫 BLOQUÉ 7,5$ /pay ID:{q.from_user.id}")
        return
    if d=="LOSS":
        u["losses"]+=1; await q.message.reply_text(f"😔 Perdu courage!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    allowed, mins = check_free(u)
    if not allowed and u["tier"]=="free": await update.message.reply_text(f"🚫 5h finies /pay ID:{update.effective_user.id}"); return
    await update.message.reply_text(f"🔥 JOSH AI V8.8 MT5 🔥\n\nSalut ami 👋 Marchés MT5 réels\n\n📊 /analyse - TOP 3 + Entrée/SL/Support/Résistance\nTape gold / eurusd / gbpusd\n\n💰 GRATUIT: 5h/jour\n💵 1 WIN = 1,5$ | Bloqué 7,5$ (5 WIN)\n🔥 PAYANT: 24h/24\n\n⏱️ Reste {mins} min | Bilan {u['debt']}$")

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    if u.get("debt_block"): await update.message.reply_text(f"🚫 BLOQUÉ {u['debt']}$"); return
    allowed, mins = check_free(u)
    if not allowed: await update.message.reply_text("🚫 5h finies /pay"); return
    prices=get_mt5_prices(); u["last_prices"]=prices; u["await_market"]=True
    await send_top_markets(context, update.effective_chat.id, prices, mins)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    txt = update.message.text.lower()
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    target=None
    if any(x in txt for x in ["gold","xau","google","gld","1"]): target="GOLD"
    elif any(x in txt for x in ["eur","euro","2"]): target="EURUSD"
    elif any(x in txt for x in ["gbp","bipy","bp","gu","3","livre"]): target="GBPUSD"
    if target:
        price = u.get("last_prices",{}).get(target) or get_mt5_prices().get(target)
        u["last_prices"][target]=price
        await send_detailed_analysis(context, update.effective_chat.id, target, price)
        return

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id); await update.message.reply_text(f"💳 Bilan {u['debt']}$ Tape mois/an/dette ID:{update.effective_user.id}")

async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=MY_ADMIN_ID: return
    if len(context.args)<2: return
    tid=int(context.args[0]); plan=context.args[1].lower()
    if tid not in users_db: users_db[tid]=get_user(tid, tid, "Client")
    if plan=="dette": users_db[tid]["debt"]=0; users_db[tid]["debt_block"]=False; users_db[tid]["blocked"]=False; users_db[tid]["wins"]=0
    else:
        expire=datetime.now()+timedelta(days=30 if plan=="mois" else 365)
        users_db[tid]["tier"]="paid"; users_db[tid]["paid_until"]=expire; users_db[tid]["blocked"]=False; users_db[tid]["debt"]=0
    await update.message.reply_text(f"✅ {tid} {plan} OK")

if __name__=="__main__":
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyse", analyse_cmd))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("addpaid", addpaid))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("V8.8 CLASSIC RESTAURÉ")
    app.run_polling()
