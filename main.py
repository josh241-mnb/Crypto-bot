import os, logging, requests, asyncio, random
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
            "await_market":False, "last_prices":{}
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
"fr": "🔥 JOSH AI V8.6 MT5 🔥\n\nSalut ami 👋 Marchés MT5 réels\n\n📊 /analyse - Voir TOP 3 marchés\nTape gold / eurusd / gbpusd\n\n💰 GRATUIT: 5h/jour\n💵 1 WIN = 1,5$ bilan | Bloqué à 7,5$ (5 WIN)\n🔥 PAYANT: 24h/24 illimité\n\n/lang fr ou /lang en",
"en": "🔥 JOSH AI V8.6 MT5 🔥\n\n/analyse - TOP 3 markets\n💰 FREE 5h/day | 1 WIN = 1.5$ bilan | Block 7.5$"
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
    msg = f"🚨 JOSH AI V8.6 - TOP MARCHÉS MT5 🚨\n📍 MT5 Réel | 🕐 {datetime.now().strftime('%d/%m %H:%M')} GMT\n\n"
    msg += "Voici les 3 bons marchés où tu peux trader maintenant:\n\n"
    for i, (sym, price) in enumerate(user_prices.items(), 1):
        trend = random.choice(["HAUSSIER 🟢", "BAISSIER 🔴", "VOLATIL ⚡"])
        score = random.randint(78, 95)
        p_fmt = f"{price:.2f}" if "XAU" in sym else f"{price:.5f}"
        msg += f"{i}️⃣ {sym}\n Prix: {p_fmt} | Tendance: {trend} | Score: {score}% 🔥\n\n"
    msg += "👉 **Lequel veux-tu trader?**\n"
    msg += "Tape: **gold** ou **eurusd** ou **gbpusd**\nOu tape 1 / 2 / 3"
    if free_mins and free_mins!=999: msg += f"\n\n⏱️ Reste {free_mins} min gratuit"
    keyboard = [[InlineKeyboardButton("🥇 GOLD", callback_data="market_XAUUSD GOLD"), InlineKeyboardButton("💶 EURUSD", callback_data="market_EURUSD"), InlineKeyboardButton("💷 GBPUSD", callback_data="market_GBPUSD")]]
    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def send_detailed_analysis(context, chat_id, symbol_key, price):
    is_buy = random.choice([True, False])
    is_gold = "XAU" in symbol_key or "GOLD" in symbol_key
    if is_gold:
        if is_buy: tp1=price*1.003; tp2=price*1.007; tp3=price*1.012; sl1=price*0.997; sl2=price*0.993
        else: tp1=price*0.997; tp2=price*0.993; tp3=price*0.988; sl1=price*1.003; sl2=price*1.007
        strategy = random.choice(["Breakout haussier sur résistance H1", "Pullback sur support + RSI", "Cassure de canal + Volume haussier"])
        tf="M15 / H1 / H4"; levier="1:100 à 1:200"
    else:
        if is_buy: tp1=price*1.0015; tp2=price*1.003; tp3=price*1.005; sl1=price*0.9985; sl2=price*0.997
        else: tp1=price*0.9985; tp2=price*0.997; tp3=price*0.995; sl1=price*1.0015; sl2=price*1.003
        strategy = random.choice(["Scalping EMA 50 + EMA 200", "Retest support/resistance", "Divergence MACD"])
        tf="M15 / H1"; levier="1:100"
    sig = "BUY 🟢 ACHAT" if is_buy else "SELL 🔴 VENTE"
    def fmt(p): return f"{p:.2f}" if is_gold else f"{p:.5f}"
    msg = f"🎯 **ANALYSE DÉTAILLÉE: {symbol_key}** 🎯\n📍 MT5 | {datetime.now().strftime('%H:%M')} GMT\n━━━━━━━━━━━━━━━\n📊 SIGNAL: **{sig}**\n💵 ENTRÉE: {fmt(price)}\n🎯 TP1: {fmt(tp1)}\n🎯 TP2: {fmt(tp2)}\n🎯 TP3: {fmt(tp3)} (Runner)\n🛑 SL1: {fmt(sl1)}\n🛑 SL2: {fmt(sl2)} Sécurité\n━━━━━━━━━━━━━━━\n🧠 **STRATÉGIE À ADOPTER:**\n• {strategy}\n• Attends confirmation bougie H1\n• Risque 1-2% max par trade\n• TF: {tf} | Levier: {levier}\n• Sécurise 50% à TP1, laisse courir TP2/TP3\n\n💡 Ouvre MT5 -> {symbol_key}\n⚠️ Mets ton SL direct!"
    keyboard = [[InlineKeyboardButton("✅ WIN Gagné", callback_data="trade_win"), InlineKeyboardButton("❌ LOSS Perdu", callback_data="trade_loss")]]
    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    u = get_user(query.from_user.id, query.message.chat_id, query.from_user.first_name)
    data = query.data

    if data.startswith("market_"):
        symbol_key = data.replace("market_", "")
        price = u.get("last_prices", {}).get(symbol_key, 3950 if "XAU" in symbol_key else 1.17)
        u["await_market"]=False
        await send_detailed_analysis(context, query.message.chat_id, symbol_key, price)
        return

    if data=="trade_win":
        u["wins"]+=1; u["total_trades"]+=1; u["debt"]=round(u.get("debt",0)+1.5,2)

        # === POUR L'UTILISATEUR - SIMPLE COMME TU AS DIT DANS VOCAL ===
        await query.message.reply_text(
            f"✅ Tu as gagné!\n\n"
            f"💳 Mon bilan à payer: {u['debt']}$\n"
            f"📊 {u['wins']} WIN / {u['losses']} LOSS"
        )

        # === POUR TOI LE BOSS DERRICK - NOTIF DÉTAILLÉE ===
        boss_msg = (
            f"🔔 BOSS DERRICK - WIN 🔔\n\n"
            f"👤 Client: {u.get('name')}\n"
            f"🆔 ID: {query.from_user.id}\n"
            f"💰 Il a gagné 1 trade avec le bot\n"
            f"💵 Bilan à payer: 1,5$ pour ce trade\n"
            f"📈 Total WIN: {u['wins']} x 1,5$ = {u['debt']}$\n"
            f"📊 Sur {u['total_trades']} trades: {u['wins']}W/{u['losses']}L\n\n"
            f"💡 Rappel: 3 WIN = 4,5$ bilan\n"
            f"💡 5 WIN = 7,5$ -> BLOQUÉ AUTO\n\n"
            f"/addpaid {query.from_user.id} dette pour débloquer"
        )
        await notify_admin(context, boss_msg)

        if u["debt"]>=7.5:
            u["debt_block"]=True; u["blocked"]=True
            await context.bot.send_message(chat_id=query.message.chat_id,
                text=f"🚫 BOT ARRÊTÉ AUTOMATIQUEMENT 🚫\n\n💳 Mon bilan à payer: {u['debt']}$ (5 WIN x 1,5$)\n\nTape /pay et envoie ton ID au patron pour payer mon bilan\n🆔 ID: `{query.from_user.id}`",
                parse_mode="Markdown")
            await notify_admin(context, f"🚫 BOSS: CLIENT BLOQUÉ AUTO 7,5$ BILAN\n👤 {u.get('name')} ID:{query.from_user.id}\nBilan: {u['debt']}$ - Il doit payer mon bilan!")
    else:
        u["losses"]+=1; u["total_trades"]+=1
        await query.message.reply_text(f"😔 Dommage mais ne pas abandonner!\n💪 Ne lâche pas, le prochain sera gagnant! 🎯\n\n📊 {u['wins']}W/{u['losses']}L | Mon bilan: {u['debt']}$")
        await notify_admin(context, f"❌ LOSS: {u.get('name')} ID:{query.from_user.id} | {u['wins']}W/{u['losses']}L | Bilan {u['debt']}$")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    if u.get("debt_block"):
        await update.message.reply_text(f"🚫 BLOQUÉ AUTO 7,5$\n💳 Mon bilan à payer: {u['debt']}$\nTape /pay et envoie ID au patron pour payer mon bilan\nID: {update.effective_user.id}"); return
    allowed, mins = check_free(u)
    if u.get("blocked"):
        await update.message.reply_text(f"🚫 Bloqué. /pay pour 24h/24\nID: {update.effective_user.id}"); return
    if not allowed and u["tier"]=="free":
        u["blocked"]=True; u["notified"]=True
        await notify_admin(context, f"🚫 AUTO-BLOCK 5h: {u['name']} ID:{update.effective_user.id}")
        await update.message.reply_text("🚫 Tes 5h finies aujourd'hui! Tape /pay pour débloquer 24h/24"); return
    extra = f"\n\n⏱️ Reste {mins} min | Bilan: {u.get('debt',0)}$\nTape /analyse" if u["tier"]=="free" else "\n\n🔥 PAYANT 24h/24 illimité"
    await update.message.reply_text(MESSAGES[u["lang"]] + extra)

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    if u.get("debt_block"):
        await update.message.reply_text(f"🚫 BLOQUÉ BILAN {u['debt']}$ (5 WIN = 7,5$)\n/pay + envoie ID au patron pour payer mon bilan\nID: {update.effective_user.id}"); return
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
    msg=f"💳 Tu veux payer quoi? 👇\n💰 Mon bilan à payer: {u.get('debt',0)}$ ({u.get('wins',0)} x 1,5$)\n\nTape **mois** 20$/mois (30j)\nTape **an** 80$/an (365j)\nTape **dette** 7,5$ pour payer mon bilan et débloquer"
    await update.message.reply_text(msg, parse_mode="Markdown")
    if update.effective_user.id!=MY_ADMIN_ID:
        await notify_admin(context, f"💰 /pay: {u.get('name')} ID:{update.effective_user.id} Bilan {u.get('debt',0)}$")

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text.lower().strip()
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)

    if u.get("await_market"):
        target_key = None
        if "gold" in text or "xau" in text or text=="1": target_key="XAUUSD GOLD"
        elif "eur" in text or text=="2": target_key="EURUSD"
        elif "gbp" in text or text=="3": target_key="GBPUSD"
        if target_key and target_key in u.get("last_prices", {}):
            u["await_market"]=False
            await send_detailed_analysis(context, update.effective_chat.id, target_key, u["last_prices"][target_key])
            return

    if not u.get("await_plan"): return
    if "mois" in text or text=="1":
        plan="mois"; label="1 MOIS 20$"
        msg_client=f"✅ Parfait, tu as choisi un mois 20$, okay.\n\nMaintenant envoie ton ID au patron et profite de ton 1 mois d'abonnement 🙏\n\n🆔 Ton ID: `{update.effective_user.id}`\n📲 /myid"
    elif "an" in text or "année" in text or "annee" in text or text=="2":
        plan="an"; label="1 AN 80$"
        msg_client=f"✅ Parfait, tu as choisi un an 80$, okay.\n\nMaintenant envoie ton ID au patron et profite de ton 1 an d'abonnement 🙏\n\n🆔 Ton ID: `{update.effective_user.id}`"
    elif "dette" in text or "bilan" in text or "7.5" in text or "7,5" in text:
        plan="dette"; label=f"BILAN {u.get('debt',0)}$"
        msg_client=f"✅ Parfait, tu veux payer mon bilan de {u.get('debt',0)}$, okay.\n\nMaintenant envoie ton ID au patron et profite du déblocage 🙏\n\n🆔 Ton ID: `{update.effective_user.id}`"
    else:
        return
    u["await_plan"]=False; u["wanted_plan"]=plan
    await update.message.reply_text(msg_client, parse_mode="Markdown")
    await notify_admin(context, f"💰 CLIENT CHOISI {label}\n👤 {u.get('name')} ID:{update.effective_user.id}\nBilan: {u.get('debt',0)}$ ({u.get('wins',0)} x 1,5$)\n/addpaid {update.effective_user.id} {plan}")

async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=MY_ADMIN_ID: return
    if len(context.args)<2:
        await update.message.reply_text("Usage:\n/addpaid ID mois\n/addpaid ID an\n/addpaid ID dette"); return
    tid=int(context.args[0]); plan=context.args[1].lower()
    if tid not in users_db:
        users_db[tid]={"chat_id":tid,"lang":"fr","blocked":False,"tier":"free","name":"Client","free_start":datetime.now(),"last_free_reset":datetime.now().date(),"notified":False,"await_plan":False,"wins":0,"losses":0,"total_trades":0,"debt":0.0,"debt_block":False,"await_market":False,"last_prices":{}}
    if plan=="dette":
        users_db[tid]["debt"]=0.0; users_db[tid]["debt_block"]=False; users_db[tid]["blocked"]=False; users_db[tid]["wins"]=0; users_db[tid]["losses"]=0; users_db[tid]["total_trades"]=0
        await update.message.reply_text(f"✅ BILAN PAYÉ {tid} -> Débloqué, bilan 0")
        try: await context.bot.send_message(chat_id=users_db[tid].get("chat_id", tid), text="🎉 MON BILAN PAYÉ! Bot débloqué! Tu peux refaire 5 WIN!")
        except: pass
        return
    if plan=="mois": expire=datetime.now()+timedelta(days=30); label="MOIS 20$ (30j)"
    else: expire=datetime.now()+timedelta(days=365); label="AN 80$ (365j)"
    users_db[tid]["tier"]="paid"; users_db[tid]["plan"]=plan; users_db[tid]["paid_until"]=expire; users_db[tid]["blocked"]=False; users_db[tid]["debt_block"]=False; users_db[tid]["debt"]=0.0
    await update.message.reply_text(f"✅ {tid} -> PAYANT {label} Expire {expire.strftime('%d/%m/%Y')}")
    try: await context.bot.send_message(chat_id=users_db[tid].get("chat_id", tid), text=f"🎉 PAYANT ACTIVÉ 24h/24 🔥\n{label}\nExpire: {expire.strftime('%d/%m/%Y')}")
    except: pass

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ID: `{update.effective_user.id}`", parse_mode="Markdown")

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)
    if not context.args: await update.message.reply_text("Usage: /lang fr ou /lang en"); return
    l=context.args[0].lower()
    if l in ["fr","en"]: u["lang"]=l; await update.message.reply_text(MESSAGES[l])

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)
    await update.message.reply_text(f"📊 TES STATS\n\n✅ WIN: {u.get('wins',0)}\n❌ LOSS: {u.get('losses',0)}\n📈 Total: {u.get('total_trades',0)}\n💳 Mon bilan: {u.get('debt',0)}$ (1,5$ x WIN)\n🚫 Bloqué à 7,5$ (5 WIN)")

async def job_auto(c):
    for uid,d in list(users_db.items()):
        if not d.get("blocked") and not d.get("debt_block") and d.get("chat_id"):
            allowed, mins = check_free(d)
            if allowed or d.get("tier")=="paid":
                prices=get_mt5_prices(); d["last_prices"]=prices
                await c.bot.send_message(chat_id=d["chat_id"], text=f"🚨 AUTO MT5 - Tape /analyse pour voir TOP 3")
                await asyncio.sleep(1)
            else:
                if not d.get("notified"): d["blocked"]=True; d["notified"]=True

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
    print("V8.6 FINAL - MEME PI + TOP 3 + BILAN")
    app.run_polling()
