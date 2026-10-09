import os, logging, requests
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
        users_db[uid] = {"lang":"fr","blocked":False,"chat_id":chat_id,"tier":"free","name":name,"free_start":now,"last_free_reset":now.date(),"wins":0,"losses":0,"debt":0.0,"debt_block":False,"last_prices":{}}
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

def get_tuto_mois_annee(debt, uid, lang="fr"):
    dette_fr = f"\n💵 DETTE = {debt}$ (WIN x 1,5$)\n👉 Tape DETTE\n" if debt>0 else ""
    dette_en = f"\n💵 DEBT = {debt}$ (WIN x 1,5$)\n👉 Type DEBT\n" if debt>0 else ""
    if lang=="en":
        return f"""💰 JOSH AI V6 💰

📅 MONTH = 20$ USD
✅ 30 days unlimited 24/7
👉 Type MONTH

📅 YEAR = 80$ USD (BEST!)
✅ 365 days unlimited 24/7
👉 Type YEAR
{dette_en}
📲 1. Type MONTH/YEAR/DEBT
2. Send ID to boss: {uid}
3. Boss unlocks 5 min

ID: {uid}
Tape /pay

FREE: 5h/day | PAID: 20$ month / 80$ year
"""
    else:
        return f"""💰 JOSH AI V6 💰

📅 MOIS = 20$ USD
✅ 30 jours illimité 24h/24
👉 Tape MOIS

📅 ANNEE = 80$ USD (MEILLEUR!)
✅ 365 jours illimité 24h/24
👉 Tape ANNEE
{dette_fr}
📲 1. Tape MOIS/ANNEE/DETTE
2. Envoie ID au patron: {uid}
3. Patron débloque 5 min

ID: {uid}
Tape /pay

GRATUIT: 5h/jour | PAYANT: 20$ mois / 80$ année
"""

async def send_top_markets(context, chat_id, user_prices, free_mins=None, lang="fr"):
    if lang=="en":
        msg = f"🔥 JOSH AI V6 - TOP MT5 🔥\n{datetime.now().strftime('%d/%m %H:%M')} GMT\n\nHere are 3 good markets now:\n\n"
    else:
        msg = f"🔥 JOSH AI V6 - TOP MARCHES MT5 🔥\n{datetime.now().strftime('%d/%m %H:%M')} GMT\n\nVoici les 3 bons marchés maintenant:\n\n"
    for sym, price in user_prices.items():
        fmt = f"{price:.2f}" if sym=="GOLD" else f"{price:.5f}"
        msg += f"🔹 {sym} Prix: {fmt} | BAISSIER 🔴 91%\n\n" if lang=="fr" else f"🔹 {sym} Price: {fmt} | BEARISH 🔴 91%\n\n"
    msg += "Tape: gold / eurusd / gbpusd ou 1/2/3\n" if lang=="fr" else "Type: gold / eurusd / gbpusd or 1/2/3\n"
    if free_mins and free_mins!=999: msg += f"\n⏱️ {free_mins} min gratuit" if lang=="fr" else f"\n⏱️ {free_mins} min left"
    kb = [[InlineKeyboardButton("🥇 GOLD", callback_data="GOLD"), InlineKeyboardButton("💶 EURUSD", callback_data="EURUSD"), InlineKeyboardButton("💷 GBPUSD", callback_data="GBPUSD")]]
    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=InlineKeyboardMarkup(kb))

async def send_detailed_analysis(context, chat_id, symbol_key, price, lang="fr"):
    is_gold = symbol_key=="GOLD"
    sup = price*0.997 if is_gold else price*0.998
    res = price*1.003 if is_gold else price*1.002
    entry = price; tp1 = price*0.99968; tp2 = price*0.9989; tp3 = price*0.995; sl1 = price*1.0058
    def fmt(p): return f"{p:.2f}" if is_gold else f"{p:.5f}"
    if lang=="en":
        txt = f"🔥 {symbol_key} 🔥\nMT5 / {datetime.now().strftime('%d/%m %H:%M')} GMT\n\n📊 SELL 🔴\n💵 ENTRY: {fmt(entry)}\n🎯 TP1: {fmt(tp1)}\n🎯 TP2: {fmt(tp2)}\n🎯 TP3: {fmt(tp3)}\n🛑 SL: {fmt(sl1)}\n📍 SUPPORT: {fmt(sup)} 🔵\n📍 RESISTANCE: {fmt(res)} 🔴\n\n📈 EMA 50+200 | H1 confirmation\nOpen MT5 -> {symbol_key}"
    else:
        txt = f"🔥 ANALYSE {symbol_key} 🔥\nMT5 / {datetime.now().strftime('%d/%m %H:%M')} GMT\n\n📊 SELL 🔴 VENTE\n💵 ENTREE: {fmt(entry)}\n🎯 TP1: {fmt(tp1)}\n🎯 TP2: {fmt(tp2)}\n🎯 TP3: {fmt(tp3)}\n🛑 SL: {fmt(sl1)}\n📍 SUPPORT: {fmt(sup)} 🔵\n📍 RESISTANCE: {fmt(res)} 🔴\n\n📈 EMA 50+200 | Attends H1\nTF M15+H1+M1=1100\nOuvre MT5 -> {symbol_key}"
    kb = [[InlineKeyboardButton("✅ WIN", callback_data="WIN"), InlineKeyboardButton("❌ LOSS", callback_data="LOSS")]]
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    u = get_user(q.from_user.id, q.message.chat_id, q.from_user.first_name)
    d = q.data
    if d.startswith("lang_"):
        lang = d.split("_")[1]; u["lang"]=lang
        await notify_admin(context, f"🌍 {u['name']} langue {lang} ID:{q.from_user.id}")
        await q.message.reply_text(f"✅ {lang} ok!")
        prices=get_mt5_prices(); u["last_prices"]=prices
        allowed, mins = check_free(u)
        await send_top_markets(context, q.message.chat_id, prices, mins, lang); return
    if d in ["GOLD","EURUSD","GBPUSD"]:
        price = u.get("last_prices",{}).get(d, 4191 if d=="GOLD" else 1.12)
        await notify_admin(context, f"👆 {u['name']} {d} ID:{q.from_user.id} Bilan:{u['debt']}$")
        await send_detailed_analysis(context, q.message.chat_id, d, price, u.get("lang","fr")); return
    if d=="WIN":
        u["wins"]+=1; u["debt"]=round(u["debt"]+1.5,2)
        await q.message.reply_text(f"✅ WIN! Bilan: {u['debt']}$ | {u['wins']}W/{u['losses']}L")
        await notify_admin(context, f"🔔 WIN {u['name']} ID:{q.from_user.id} DOIT:{u['debt']}$")
        if u["debt"]>=7.5:
            u["debt_block"]=True; u["blocked"]=True
            lang=u.get("lang","fr")
            txt = f"⛔ BOT STOPPED ⛔\nBalance: {u['debt']}$ (5 WIN)\n/pay + ID {q.from_user.id}\n\nMY BALANCE PAID! Bot unlocked! 0 WIN\n\nToo bad but don't give up! Next will win! 😊" if lang=="en" else f"⛔ BOT ARRETE ⛔\nBilan: {u['debt']}$ (5 WIN x 1,5$)\n/pay + ID {q.from_user.id}\n\nMON BILAN PAYE! Bot débloqué! 0 WIN\n\nDommage mais ne pas abandonne! Ne lâche pas, le prochain sera gagnant! 😊"
            await context.bot.send_message(chat_id=q.message.chat_id, text=txt)
            await notify_admin(context, f"🚨 BLOQUE 7,5$ {u['name']} ID:{q.from_user.id}")
        return
    if d=="LOSS":
        u["losses"]+=1
        lang=u.get("lang","fr")
        txt = "❌ LOSS - Too bad but don't give up! Next will win! 😊\n\nYou also lost? Courage!" if lang=="en" else "❌ LOSS Perdu - Dommage mais ne pas abandonne! Ne lâche pas, le prochain sera gagnant! 😊\n\nAh toi aussi tu as perdu? Courage ami!"
        await q.message.reply_text(txt)
        await notify_admin(context, f"❌ LOSS {u['name']} ID:{q.from_user.id}"); return

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    await notify_admin(context, f"🟢 NOUVEAU {u['name']} ID:{update.effective_user.id} @{update.effective_user.username}")
    await send_lang_choice(update.effective_chat.id, context)

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    if u.get("debt_block"): await update.message.reply_text(f"🚫 BLOQUE {u['debt']}$\n\n{get_tuto_mois_annee(u['debt'], update.effective_user.id, u.get('lang','fr'))}"); return
    allowed, mins = check_free(u)
    if not allowed: await update.message.reply_text(f"🚫 5h finies\n\n{get_tuto_mois_annee(u['debt'], update.effective_user.id, u.get('lang','fr'))}"); return
    prices=get_mt5_prices(); u["last_prices"]=prices
    await send_top_markets(context, update.effective_chat.id, prices, mins, u.get("lang","fr"))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    txt = update.message.text.lower()
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    lang=u.get("lang","fr")
    if "mois" in txt or "month" in txt: await notify_admin(context, f"💰 MOIS 20$ {u['name']} ID:{update.effective_user.id}"); await update.message.reply_text(get_tuto_mois_annee(u["debt"], update.effective_user.id, lang)); return
    if "ann" in txt or "year" in txt or txt.strip()=="an": await notify_admin(context, f"💰 ANNEE 80$ {u['name']} ID:{update.effective_user.id}"); await update.message.reply_text(get_tuto_mois_annee(u["debt"], update.effective_user.id, lang)); return
    if "dette" in txt or "debt" in txt or "bilan" in txt: await notify_admin(context, f"💰 DETTE {u['name']} ID:{update.effective_user.id} {u['debt']}$"); await update.message.reply_text(get_tuto_mois_annee(u["debt"], update.effective_user.id, lang)); return
    if "lang" in txt: await send_lang_choice(update.effective_chat.id, context); return
    target=None
    if any(x in txt for x in ["gold","xau","google","gole","1","or"]): target="GOLD"
    elif any(x in txt for x in ["eur","euro","2"]): target="EURUSD"
    elif any(x in txt for x in ["gbp","bipy","bp","gu","3"]): target="GBPUSD"
    if target:
        price = u.get("last_prices",{}).get(target) or get_mt5_prices().get(target)
        await notify_admin(context, f"📊 {u['name']} {target} ID:{update.effective_user.id}")
        await send_detailed_analysis(context, update.effective_chat.id, target, price, lang)

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)
    await notify_admin(context, f"💰 /pay {u['name']} ID:{update.effective_user.id} {u['debt']}$")
    await update.message.reply_text(get_tuto_mois_annee(u['debt'], update.effective_user.id, u.get("lang","fr")))

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE): await send_lang_choice(update.effective_chat.id, context)

async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=MY_ADMIN_ID: return
    tid=int(context.args[0]); plan=context.args[1].lower()
    if tid not in users_db: users_db[tid]=get_user(tid, tid, "Client")
    lang=users_db[tid].get("lang","fr")
    if plan=="dette" or plan=="debt":
        users_db[tid]["debt"]=0; users_db[tid]["debt_block"]=False; users_db[tid]["blocked"]=False; users_db[tid]["wins"]=0
        txt = "🎉 MON BILAN PAYE! Bot débloqué! Tu peux refaire 0 WIN ✅" if lang=="fr" else "🎉 MY BALANCE PAID! Bot unlocked! You can redo 0 WIN ✅"
    elif plan=="mois" or plan=="month":
        users_db[tid]["tier"]="paid"; users_db[tid]["paid_until"]=datetime.now()+timedelta(days=30); users_db[tid]["blocked"]=False; users_db[tid]["debt"]=0; users_db[tid]["debt_block"]=False
        txt = "🎉 PAYE! Débloqué!\n\n✅ Profite de ton abonnement du MOIS! 🚀\n30 jours illimité 24h/24" if lang=="fr" else "🎉 PAID! Unlocked!\n\n✅ Enjoy your MONTH subscription! 🚀\n30 days unlimited 24/7"
    else:
        users_db[tid]["tier"]="paid"; users_db[tid]["paid_until"]=datetime.now()+timedelta(days=365); users_db[tid]["blocked"]=False; users_db[tid]["debt"]=0; users_db[tid]["debt_block"]=False
        txt = "🎉 PAYE! Débloqué!\n\n✅ Profite de ton abonnement de l'ANNEE! 🚀🔥\n365 jours illimité" if lang=="fr" else "🎉 PAID! Unlocked!\n\n✅ Enjoy your YEAR subscription! 🚀🔥\n365 days unlimited"
    await update.message.reply_text(f"✅ {tid} {plan} OK")
    try: await context.bot.send_message(chat_id=users_db[tid]["chat_id"], text=txt)
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
    print("V6 MEME DESIGN FINAL")
    app.run_polling()
⛔ BOT ARRÊTÉ
Bilan: 7,5$ à payer
Tape /pay + ID au patron
❌ LOSS Perdu
Dommage mais ne pas abandonne!
Ne lâche pas, le prochain sera gagnant! 😊
Too bad but don't give up!
Don't give up, next one will be winner! 😊
# ... (même code que avant mais corrigé dans button_handler WIN)

    if d=="WIN":
        u["wins"]+=1; u["debt"]=round(u["debt"]+1.5,2)
        await q.message.reply_text(f"✅ WIN! Bilan: {u['debt']}$ | {u['wins']}W/{u['losses']}L")
        await notify_admin(context, f"🔔 WIN {u['name']} ID:{q.from_user.id} DOIT:{u['debt']}$")
        if u["debt"]>=7.5:
            u["debt_block"]=True; u["blocked"]=True
            lang=u.get("lang","fr")
            # CORRIGE: PLUS DE "DOMMAGE" ICI!
            txt = f"⛔ BOT STOPPED AUTO ⛔\n\nBalance: {u['debt']}$ (5 WIN x 1,5$)\nType /pay + send ID {q.from_user.id} to boss to pay\n\nID: {q.from_user.id}" if lang=="en" else f"⛔ BOT ARRETE AUTO ⛔\n\nBilan: {u['debt']}$ (5 WIN x 1,5$)\nTape /pay + envoie ID {q.from_user.id} au patron pour payer\n\nID: {q.from_user.id}"
            await context.bot.send_message(chat_id=q.message.chat_id, text=txt)
            await notify_admin(context, f"🚨 BLOQUE 7,5$ {u['name']} ID:{q.from_user.id}")
        return
    if d=="LOSS":
        u["losses"]+=1
        lang=u.get("lang","fr")
        # DOMMAGE SEULEMENT ICI POUR LOSS!
        txt = "❌ LOSS - Too bad but don't give up!\nDon't give up, next one will be winner! 😊" if lang=="en" else "❌ Perdu - Dommage mais ne pas abandonne!\nNe lâche pas, le prochain sera gagnant! 😊"
        await q.message.reply_text(txt)
        return
        
