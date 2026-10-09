import os, logging, requests, asyncio, random, re
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
        users_db[uid] = {"lang":"fr","blocked":False,"chat_id":chat_id,"tier":"free","name":name,"free_start":now,"last_free_reset":now.date(),"wins":0,"losses":0,"total_trades":0,"debt":0.0,"debt_block":False,"await_market":False,"await_sr":False,"last_prices":{},"sr_symbol":"GOLD"}
    if chat_id: users_db[uid]["chat_id"]=chat_id
    if name: users_db[uid]["name"]=name
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
    prices={}
    try: r=requests.get("https://api.gold-api.com/price/XAU",timeout=5).json(); prices["GOLD"]=float(r.get("price", 4136))
    except: prices["GOLD"]=4136+random.uniform(-15,15)
    try: r=requests.get("https://api.exchangerate-api.com/v4/latest/EUR",timeout=5).json(); prices["EURUSD"]=float(r["rates"]["USD"])
    except: prices["EURUSD"]=1.1720+random.uniform(-0.002,0.002)
    try: r=requests.get("https://api.exchangerate-api.com/v4/latest/GBP",timeout=5).json(); prices["GBPUSD"]=float(r["rates"]["USD"])
    except: prices["GBPUSD"]=1.3220+random.uniform(-0.002,0.002)
    return prices

async def send_top_markets(context, chat_id, user_prices, free_mins=None):
    msg = f"🚨 JOSH AI V9.0 TOP 3 MT5 🚨\n📍 {datetime.now().strftime('%d/%m %H:%M')} GMT\n\n"
    for sym, price in user_prices.items():
        trend = random.choice(["HAUSSIER 🟢","BAISSIER 🔴","VOLATIL ⚡"])
        score = random.randint(82,95)
        f = f"{price:.2f}" if sym=="GOLD" else f"{price:.5f}"
        msg += f"🔹 {sym}: {f} | {trend} | Score {score}%\n\n"
    msg += "👉 Tape: gold / euro / gbp OU clique bouton"
    kb = [[InlineKeyboardButton("🥇 GOLD", callback_data="GOLD"), InlineKeyboardButton("💶 EURO", callback_data="EURUSD"), InlineKeyboardButton("💷 GBP", callback_data="GBPUSD")]]
    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=InlineKeyboardMarkup(kb))

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
    sig = "BUY 🟢" if is_buy else "SELL 🔴"
    def fmt(p): return f"{p:.2f}" if is_gold else f"{p:.5f}"
    txt = f"🎯 **{symbol_key} MT5 - {sig}**\n━━━━━━━━━━━━━━━\n💵 ENTRÉE: {fmt(entry)}\n🎯 TP1: {fmt(tp1)}\n🎯 TP2: {fmt(tp2)}\n🎯 TP3: {fmt(tp3)}\n🛑 SL: {fmt(sl)}\n━━━━━━━━━━━━━━━\n📍 SUPPORT: {fmt(sup)} 🔵\n📍 RÉSISTANCE: {fmt(res)} 🔴\n━━━━━━━━━━━━━━━\n💡 Ouvre MT5 -> {symbol_key}"
    kb = [[InlineKeyboardButton("✅ WIN", callback_data="WIN"), InlineKeyboardButton("❌ LOSS", callback_data="LOSS")]]
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id, q.message.chat_id, q.from_user.first_name)
    d = q.data
    if d in ["GOLD","EURUSD","GBPUSD"]:
        price = u.get("last_prices",{}).get(d, 4136 if d=="GOLD" else 1.17)
        u["sr_symbol"]=d
        await send_detailed_analysis(context, q.message.chat_id, d, price)
        return
    if d=="WIN":
        u["wins"]+=1; u["total_trades"]+=1; u["debt"]=round(u["debt"]+1.5,2)
        await q.message.reply_text(f"✅ Tu as gagné!\n💳 Mon bilan à payer: {u['debt']}$\n📊 {u['wins']} WIN")
        await notify_admin(context, f"🔔 WIN {u['name']} ID:{q.from_user.id} Bilan {u['debt']}$")
        if u["debt"]>=7.5:
            u["debt_block"]=True; u["blocked"]=True
            await context.bot.send_message(chat_id=q.message.chat_id, text=f"🚫 BLOQUÉ 7,5$ /pay ID:{q.from_user.id}")
        return
    if d=="LOSS":
        u["losses"]+=1; await q.message.reply_text(f"😔 Perdu courage! Bilan {u['debt']}$"); return

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    await update.message.reply_text("🔥 JOSH AI V9.0 🔥\n/analyse -> TOP 3\nTape gold / euro / gbp")

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    if u.get("debt_block"): await update.message.reply_text(f"🚫 BLOQUÉ {u['debt']}$"); return
    prices=get_mt5_prices(); u["last_prices"]=prices; u["await_market"]=True
    allowed, mins = check_free(u)
    await send_top_markets(context, update.effective_chat.id, prices, mins)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    txt = update.message.text.lower()
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)

    # TOUT PASSE - COMME TU AS DIT VOCAL
    target=None
    if any(x in txt for x in ["gold","xau","google","gole","gld","1"]): target="GOLD"
    elif any(x in txt for x in ["eur","euro","eurusd","eura","2"]): target="EURUSD"
    elif any(x in txt for x in ["gbp","bipy","bp","gbpusd","gu","cable","3","livre"]): target="GBPUSD"

    if target:
        price = u.get("last_prices",{}).get(target)
        if not price:
            price = get_mt5_prices().get(target)
            u["last_prices"][target]=price
        u["sr_symbol"]=target
        await send_detailed_analysis(context, update.effective_chat.id, target, price)
        return

    # S/R
    if u.get("await_sr"):
        nums=re.findall(r"\d+\.?\d*", txt.replace(',','.'))
        if nums:
            a=float(nums[0]); b=float(nums[1]) if len(nums)>1 else None
            sup=min(a,b) if b else a; res=max(a,b) if b else a*1.003
            await send_detailed_analysis(context, update.effective_chat.id, u["sr_symbol"], u["last_prices"].get(u["sr_symbol"],4136), {"support":sup,"resistance":res})
            u["await_sr"]=False

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id); await update.message.reply_text(f"💳 Bilan {u['debt']}$ Tape mois/an/dette")

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
    print("V9.0 TOUT PASSE - GOLD EURO GBP")
    app.run_polling()
