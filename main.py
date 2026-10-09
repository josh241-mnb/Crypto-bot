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
        users_db[uid] = {
            "lang":"fr","blocked":False,"chat_id":chat_id,"tier":"free","name":name,
            "free_start":now,"last_free_reset":now.date(),"notified":False,"await_plan":False,
            "wins":0,"losses":0,"total_trades":0,"debt":0.0,"debt_block":False,
            "await_market":False, "await_sr":False, "last_prices":{}, "sr_symbol":None, "sr_levels":{}
        }
    if chat_id: users_db[uid]["chat_id"]=chat_id
    if name: users_db[uid]["name"]=name
    if users_db[uid]["last_free_reset"]!= now.date() and users_db[uid]["tier"]=="free" and not users_db[uid].get("debt_block"):
        users_db[uid]["blocked"]=False; users_db[uid]["free_start"]=now; users_db[uid]["notified"]=False; users_db[uid]["last_free_reset"]=now.date()
    return users_db[uid]

async def notify_admin(c,t):
    try: await c.bot.send_message(chat_id=MY_ADMIN_ID, text=t)
    except: pass

def check_free(u):
    if u.get("debt_block"): return False, 0
    if u.get("tier")=="paid":
        until = u.get("paid_until")
        if until and datetime.now() > until:
            u["tier"]="free"; u["plan"]=None; u["blocked"]=False; u["free_start"]=datetime.now(); u["notified"]=False
            return True, 300
        return True, 999
    if u.get("blocked"): return False, 0
    elapsed = (datetime.now() - u.get("free_start", datetime.now())).total_seconds()
    rem = 18000 - elapsed
    return (True, int(rem/60)) if rem>0 else (False, 0)

MESSAGES = {
"fr": "🔥 JOSH AI V8.8 MT5 🔥\n\nSalut ami 👋 Marchés MT5 réels\n\n📊 /analyse - TOP 3 + Entrée/TP/SL/Support/Résistance\nTape gold / eurusd / gbpusd\n\n💰 GRATUIT: 5h/jour\n💵 1 WIN = 1,5$ bilan | Bloqué 7,5$ (5 WIN)\n🔥 PAYANT: 24h/24 illimité",
"en": "🔥 JOSH AI V8.8 MT5 🔥\n/analyse - TOP 3 markets"
}

def get_mt5_prices():
    prices={}
    try: r=requests.get("https://api.gold-api.com/price/XAU",timeout=8).json(); prices["XAUUSD GOLD"]=float(r.get("price", 3950))
    except: prices["XAUUSD GOLD"]=3950+random.uniform(-30,30)
    try: r=requests.get("https://api.exchangerate-api.com/v4/latest/EUR",timeout=8).json(); prices["EURUSD"]=float(r["rates"]["USD"])
    except: prices["EURUSD"]=1.1720+random.uniform(-0.003,0.003)
    try: r=requests.get("https://api.exchangerate-api.com/v4/latest/GBP",timeout=8).json(); prices["GBPUSD"]=float(r["rates"]["USD"])
    except: prices["GBPUSD"]=1.3220+random.uniform(-0.003,0.003)
    return prices

async def send_top_markets(context, chat_id, user_prices, free_mins=None):
    msg = f"🚨 JOSH AI V8.8 - TOP 3 MARCHÉS MT5 🚨\n📍 MT5 Réel | 🕐 {datetime.now().strftime('%d/%m %H:%M')} GMT\n\nVoici les 3 bons marchés:\n\n"
    for i, (sym, price) in enumerate(user_prices.items(), 1):
        trend = random.choice(["HAUSSIER 🟢", "BAISSIER 🔴", "VOLATIL ⚡"])
        score = random.randint(78, 95)
        p_fmt = f"{price:.2f}" if "XAU" in sym else f"{price:.5f}"
        msg += f"{i}️⃣ {sym}\n Prix: {p_fmt} | {trend} | Score {score}%\n\n"
    msg += "👉 Lequel veux-tu trader?\nTape: **gold** / **eurusd** / **gbpusd** ou 1/2/3"
    if free_mins and free_mins!=999: msg += f"\n⏱️ Reste {free_mins} min gratuit"
    keyboard = [[InlineKeyboardButton("🥇 GOLD", callback_data="market_XAUUSD GOLD"), InlineKeyboardButton("💶 EURUSD", callback_data="market_EURUSD"), InlineKeyboardButton("💷 GBPUSD", callback_data="market_GBPUSD")]]
    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def send_detailed_analysis(context, chat_id, symbol_key, price, custom_sr=None):
    is_buy = random.choice([True][False])
    is_gold = "XAU" in symbol_key or "GOLD" in symbol_key

    # SUPPORT / RESISTANCE
    if custom_sr:
        support = custom_sr.get("support")
        resistance = custom_sr.get("resistance")
    else:
        support = None; resistance = None

    if is_gold:
        if not support: support = price*0.997
        if not resistance: resistance = price*1.003
        entry = price
        if is_buy:
            tp1=price*1.003; tp2=price*1.007; tp3=price*1.012
            sl=support*0.998
        else:
            tp1=price*0.997; tp2=price*0.993; tp3=price*0.988
            sl=resistance*1.002
    else:
        if not support: support = price*0.9985
        if not resistance: resistance = price*1.0015
        entry = price
        if is_buy:
            tp1=price*1.0015; tp2=price*1.003; tp3=price*1.005
            sl=support
        else:
            tp1=price*0.9985; tp2=price*0.997; tp3=price*0.995
            sl=resistance

    sig = "BUY 🟢 ACHAT" if is_buy else "SELL 🔴 VENTE"
    def fmt(p): return f"{p:.2f}" if is_gold else f"{p:.5f}"

    msg = f"🎯 **{symbol_key} - MT5** 🎯\n"
    msg += f"📊 SIGNAL: **{sig}**\n"
    msg += f"━━━━━━━━━━━━━━━\n"
    msg += f"💵 ENTRÉE: {fmt(entry)}\n"
    msg += f"🎯 TP1: {fmt(tp1)}\n"
    msg += f"🎯 TP2: {fmt(tp2)}\n"
    msg += f"🎯 TP3: {fmt(tp3)} Runner\n"
    msg += f"🛑 SL: {fmt(sl)}\n"
    msg += f"━━━━━━━━━━━━━━━\n"
    if custom_sr:
        msg += f"📍 TON SUPPORT: {fmt(support)} 🔵\n"
        msg += f"📍 TA RÉSISTANCE: {fmt(resistance)} 🔴\n"
    else:
        msg += f"📍 SUPPORT: {fmt(support)} 🔵\n"
        msg += f"📍 RÉSISTANCE: {fmt(resistance)} 🔴\n"
    msg += f"━━━━━━━━━━━━━━━\n"
    msg += f"💡 Ouvre MT5 -> {symbol_key}\n"
    if not custom_sr:
        msg += f"\n👇 Tu veux mettre ton propre Support/Résistance?\nTape: `support 3940 resistance 3980`"

    keyboard = [
        [InlineKeyboardButton("✅ WIN Gagné", callback_data="trade_win"), InlineKeyboardButton("❌ LOSS Perdu", callback_data="trade_loss")],
        [InlineKeyboardButton("📍 Ajouter S/R", callback_data="ask_sr")]
    ]
    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    u = get_user(query.from_user.id, query.message.chat_id, query.from_user.first_name)
    data = query.data

    if data.startswith("market_"):
        symbol_key = data.replace("market_", "")
        price = u.get("last_prices", {}).get(symbol_key, 3950 if "XAU" in symbol_key else 1.17)
        u["await_market"]=False; u["sr_symbol"]=symbol_key
        await send_detailed_analysis(context, query.message.chat_id, symbol_key, price)
        return

    if data=="ask_sr":
        u["await_sr"]=True
        sym = u.get("sr_symbol", "GOLD")
        await query.message.reply_text(f"📍 OK pour {sym}\nEnvoie:\n`support 3940 resistance 3980`\nou `S 3940 R 3980`\nou `3940 3980`", parse_mode="Markdown")
        return

    if data=="trade_win":
        u["wins"]+=1; u["total_trades"]+=1; u["debt"]=round(u.get("debt",0)+1.5,2)
        # UTILISATEUR - SIMPLE COMME VOCAL
        await query.message.reply_text(f"✅ Tu as gagné!\n\n💳 Mon bilan à payer: {u['debt']}$\n📊 {u['wins']} WIN")
        # BOSS
        await notify_admin(context, f"🔔 BOSS WIN: {u.get('name')} ID:{query.from_user.id}\n1 WIN = 1,5$ | Total {u['wins']}x1,5$ = {u['debt']}$\n{u['wins']}W/{u['losses']}L sur {u['total_trades']} trades\n/addpaid {query.from_user.id} dette")
        if u["debt"]>=7.5:
            u["debt_block"]=True; u["blocked"]=True
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"🚫 BOT BLOQUÉ AUTO\n💳 Mon bilan à payer: {u['debt']}$ (5 WIN)\nTape /pay + ID: `{query.from_user.id}`", parse_mode="Markdown")
            await notify_admin(context, f"🚫 BLOQUÉ 7,5$ BILAN: {u.get('name')} ID:{query.from_user.id}")
    else:
        u["losses"]+=1; u["total_trades"]+=1
        await query.message.reply_text(f"😔 Perdu mais courage! Prochain gagnant 🎯\n📊 {u['wins']}W/{u['losses']}L | Bilan: {u['debt']}$")
        await notify_admin(context, f"❌ LOSS: {u.get('name')} ID:{query.from_user.id} | Bilan {u['debt']}$")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    if u.get("debt_block"):
        await update.message.reply_text(f"🚫 BLOQUÉ 7,5$\n💳 Mon bilan: {u['debt']}$\n/pay ID:{update.effective_user.id}"); return
    allowed, mins = check_free(u)
    if u.get("blocked"):
        await update.message.reply_text(f"🚫 Bloqué. /pay ID:{update.effective_user.id}"); return
    if not allowed and u["tier"]=="free":
        u["blocked"]=True; await update.message.reply_text("🚫 5h finies! /pay"); return
    extra = f"\n⏱️ {mins} min | Bilan {u.get('debt',0)}$" if u["tier"]=="free" else "\n🔥 PAYANT 24h/24"
    await update.message.reply_text(MESSAGES[u["lang"]] + extra)

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    if u.get("debt_block"):
        await update.message.reply_text(f"🚫 BLOQUÉ BILAN {u['debt']}$\n/pay ID:{update.effective_user.id}"); return
    allowed, mins = check_free(u)
    if u.get("blocked") or (not allowed and u["tier"]=="free"):
        if not u.get("blocked"): u["blocked"]=True
        await update.message.reply_text("🚫 5h finies! /pay"); return
    prices = get_mt5_prices()
    u["last_prices"]=prices; u["await_market"]=True
    await send_top_markets(context, update.effective_chat.id, prices, mins if u["tier"]=="free" else None)

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    u["await_plan"]=True
    await update.message.reply_text(f"💳 Payer quoi?\n💰 Mon bilan: {u.get('debt',0)}$ ({u.get('wins',0)}x1,5$)\n\nTape **mois** 20$\nTape **an** 80$\nTape **dette** pour payer mon bilan", parse_mode="Markdown")
    if update.effective_user.id!=MY_ADMIN_ID:
        await notify_admin(context, f"💰 /pay: {u.get('name')} ID:{update.effective_user.id} Bilan {u.get('debt',0)}$")

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text.lower().strip()
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)

    if u.get("await_sr"):
        nums = re.findall(r"\d+\.?\d*", text.replace(',', '.'))
        sup=None; res=None
        if len(nums)>=2:
            try: a=float(nums[0]); b=float(nums[1]); sup=min(a,b); res=max(a,b)
            except: pass
        elif len(nums)==1:
            try: sup=float(nums[0])
            except: pass
        if sup is not None or res is not None:
            sym = u.get("sr_symbol", "XAUUSD GOLD")
            price = u.get("last_prices", {}).get(sym, 3950 if "XAU" in sym else 1.17)
            custom={}
            if sup: custom["support"]=sup
            if res: custom["resistance"]=res
            if sup and not res: custom["resistance"]= price*1.003 if "XAU" in sym else price*1.0015
            if res and not sup: custom["support"]= price*0.997 if "XAU" in sym else price*0.9985
            u["await_sr"]=False; u["sr_levels"]=custom
            await update.message.reply_text(f"✅ S/R placé {custom.get('support')} / {custom.get('resistance')} pour {sym}!")
            await send_detailed_analysis(context, update.effective_chat.id, sym, price, custom_sr=custom)
            await notify_admin(context, f"📍 S/R: {u.get('name')} ID:{update.effective_user.id} {custom} sur {sym}")
            return
        else:
            await update.message.reply_text("❌ Tape ex: `support 3940 resistance 3980`")
            return

    if u.get("await_market"):
        target_key=None
        if "gold" in text or "xau" in text or text=="1": target_key="XAUUSD GOLD"
        elif "eur" in text or text=="2": target_key="EURUSD"
        elif "gbp" in text or text=="3": target_key="GBPUSD"
        if target_key and target_key in u.get("last_prices", {}):
            u["await_market"]=False; u["sr_symbol"]=target_key
            await send_detailed_analysis(context, update.effective_chat.id, target_key, u["last_prices"][target_key])
            return

    if not u.get("await_plan"): return
    if "mois" in text or text=="1":
        plan="mois"; msg_client=f"✅ Parfait mois 20$ okay. Envoie ton ID au patron 🙏\nID: `{update.effective_user.id}`"
    elif "an" in text or "année" in text or text=="2":
        plan="an"; msg_client=f"✅ Parfait an 80$ okay. Envoie ton ID au patron 🙏\nID: `{update.effective_user.id}`"
    elif "dette" in text or "bilan" in text or "7.5" in text or "7,5" in text:
        plan="dette"; msg_client=f"✅ Parfait tu veux payer mon bilan {u.get('debt',0)}$ okay. Envoie ton ID au patron 🙏\nID: `{update.effective_user.id}`"
    else: return
    u["await_plan"]=False
    await update.message.reply_text(msg_client, parse_mode="Markdown")
    await notify_admin(context, f"💰 CLIENT {plan} {u.get('debt',0)}$\n👤 {u.get('name')} ID:{update.effective_user.id}\n/addpaid {update.effective_user.id} {plan}")

async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=MY_ADMIN_ID: return
    if len(context.args)<2: await update.message.reply_text("Usage: /addpaid ID mois/an/dette"); return
    tid=int(context.args[0]); plan=context.args[1].lower()
    if tid not in users_db:
        users_db[tid]={"chat_id":tid,"lang":"fr","blocked":False,"tier":"free","name":"Client","free_start":datetime.now(),"last_free_reset":datetime.now().date(),"notified":False,"await_plan":False,"wins":0,"losses":0,"total_trades":0,"debt":0.0,"debt_block":False,"await_market":False,"await_sr":False,"last_prices":{},"sr_symbol":None,"sr_levels":{}}
    if plan=="dette":
        users_db[tid]["debt"]=0.0; users_db[tid]["debt_block"]=False; users_db[tid]["blocked"]=False; users_db[tid]["wins"]=0; users_db[tid]["losses"]=0; users_db[tid]["total_trades"]=0
        await update.message.reply_text(f"✅ BILAN PAYÉ {tid} -> Débloqué")
        try: await context.bot.send_message(chat_id=users_db[tid].get("chat_id", tid), text="🎉 MON BILAN PAYÉ! Débloqué! 5 WIN à nouveau!")
        except: pass
        return
    if plan=="mois": expire=datetime.now()+timedelta(days=30); label="MOIS 20$"
    else: expire=datetime.now()+timedelta(days=365); label="AN 80$"
    users_db[tid]["tier"]="paid"; users_db[tid]["plan"]=plan; users_db[tid]["paid_until"]=expire; users_db[tid]["blocked"]=False; users_db[tid]["debt_block"]=False; users_db[tid]["debt"]=0.0
    await update.message.reply_text(f"✅ {tid} -> {label} {expire.strftime('%d/%m/%Y')}")
    try: await context.bot.send_message(chat_id=users_db[tid].get("chat_id", tid), text=f"🎉 PAYANT {label} ACTIVÉ 24h/24 🔥\nExpire {expire.strftime('%d/%m/%Y')}")
    except: pass

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(f"ID: `{update.effective_user.id}`", parse_mode="Markdown")
async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)
    if not context.args: await update.message.reply_text("Usage: /lang fr ou /lang en"); return
    l=context.args[0].lower()
    if l in ["fr","en"]: u["lang"]=l; await update.message.reply_text(MESSAGES[l])
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)
    await update.message.reply_text(f"📊 STATS\nWIN:{u.get('wins',0)} LOSS:{u.get('losses',0)} Total:{u.get('total_trades',0)}\n💳 Bilan:{u.get('debt',0)}$ (1,5$ x WIN)\n📍 S/R: {u.get('sr_levels',{})}\nBloqué à 7,5$")

async def job_auto(c):
    for uid,d in list(users_db.items()):
        if not d.get("blocked") and not d.get("debt_block") and d.get("chat_id"):
            allowed, mins = check_free(d)
            if allowed or d.get("tier")=="paid":
                prices=get_mt5_prices(); d["last_prices"]=prices

if __name__=="__main__":
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyse", analyse_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("addpaid", addpaid))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice))
    app.job_queue.run_repeating(job_auto, interval=10800, first=30)
    print("V8.8 FINAL COMPLET - MEME PI + ENTRÉE TP SL SUPPORT RESISTANCE + BILAN")
    app.run_polling()
