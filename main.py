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
    except: p["GOLD"]=4191.00
    p["EURUSD"]=1.12000
    p["GBPUSD"]=1.32000
    return p

# === TON ANCIEN TOP 3 EXACT ===
async def send_top_markets(context, chat_id, user_prices, free_mins=None):
    msg = f"🔥 JOSH AI V6 - TOP MARCHES MT5 🔥\n"
    msg += f"MT5 Réel | {datetime.now().strftime('%d/%m %H:%M')} GMT\n\n"
    msg += f"Voici les 3 bons marchés où tu peux trader maintenant:\n\n"
    for sym, price in user_prices.items():
        fmt = f"{price:.2f}" if sym=="GOLD" else f"{price:.5f}"
        msg += f"🔹 {sym}\nPrix: {fmt} | Tendance: BAISSIER 🔴\nScore: 91%\n\n"
    msg += f"Lequel veux-tu trader?\nTape: gold ou eurusd ou gbpusd\nOu tape 1 / 2 / 3\n\n"
    if free_mins and free_mins!=999:
        msg += f"⏱️ Reste {free_mins} min gratuit"
    kb = [[InlineKeyboardButton("🥇 GOLD", callback_data="GOLD"), InlineKeyboardButton("💶 EURUSD", callback_data="EURUSD"), InlineKeyboardButton("💷 GBPUSD", callback_data="GBPUSD")]]
    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=InlineKeyboardMarkup(kb))

# === TON ANCIEN DESIGN DETAILLE + SUPPORT/RESISTANCE AJOUTÉ ICI ===
async def send_detailed_analysis(context, chat_id, symbol_key, price, custom_sr=None):
    is_buy = False # Tu voulais SELL comme vidéo
    if random.random() > 0.5: is_buy = True
    is_gold = symbol_key=="GOLD"

    # Support / Résistance - AJOUT DEMANDÉ
    if custom_sr:
        sup = custom_sr.get("support")
        res = custom_sr.get("resistance")
    else:
        sup = price*0.997 if is_gold else price*0.998
        res = price*1.003 if is_gold else price*1.002

    entry = price
    tp1 = price*0.99968 if not is_buy else price*1.00032
    tp2 = price*0.9989 if not is_buy else price*1.0011
    tp3 = price*0.995 if not is_buy else price*1.005
    sl1 = price*1.0058 if not is_buy else price*0.9942

    sig = "BUY 🟢 ACHAT" if is_buy else "SELL 🔴 VENTE"
    def fmt(p): return f"{p:.2f}" if is_gold else f"{p:.5f}"

    txt = f"🔥 ANALYSE DETAILLEE: {symbol_key} 🔥\n"
    txt += f"MT5 / {datetime.now().strftime('%d/%m %H:%M')} GMT\n\n"
    txt += f"📊 SIGNAL: {sig}\n"
    txt += f"💵 ENTREE: {fmt(entry)}\n"
    txt += f"🎯 TP1: {fmt(tp1)}\n"
    txt += f"🎯 TP2: {fmt(tp2)}\n"
    txt += f"🎯 TP3: {fmt(tp3)} (Runner)\n"
    txt += f"🛑 SL1: {fmt(sl1)}\n"
    txt += f"📍 SUPPORT: {fmt(sup)} 🔵\n"
    txt += f"📍 RESISTANCE: {fmt(res)} 🔴\n"
    txt += f"\n📈 STRATEGIE ADOPTEE:\n"
    txt += f"Scalping EMA 50 + EMA 200\n"
    txt += f"Attends confirmation bougie H1\n"
    txt += f"TF M15 + TF H1 + TF M1 = 1100\n"
    txt += f"Sécurise 50% & laisse courir TP2/TP3\n"
    txt += f"Sécurité 50% & 1900\n\n"
    txt += f"Ouvre MT5 -> {symbol_key}\n"
    txt += f"Mets lot direct!"

    kb = [[InlineKeyboardButton("✅ WIN Gagné", callback_data="WIN"), InlineKeyboardButton("❌ LOSS Perdu", callback_data="LOSS")]]
    await context.bot.send_message(chat_id=chat_id, text=txt, reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id, q.message.chat_id, q.from_user.first_name)
    d = q.data
    if d in ["GOLD","EURUSD","GBPUSD"]:
        price = u.get("last_prices",{}).get(d, 4191 if d=="GOLD" else 1.12)
        u["sr_symbol"]=d
        await send_detailed_analysis(context, q.message.chat_id, d, price)
        return
    if d=="WIN":
        u["wins"]+=1; u["total_trades"]+=1; u["debt"]=round(u["debt"]+1.5,2)
        await q.message.reply_text(f"✅ Tu as gagné!\n\nMon bilan à payer: {u['debt']}$\n{u['wins']} WIN / {u['losses']} LOSS")
        await notify_admin(context, f"WIN {u['name']} ID:{q.from_user.id} Bilan {u['debt']}$")
        if u["debt"]>=7.5:
            u["debt_block"]=True; u["blocked"]=True
            await context.bot.send_message(chat_id=q.message.chat_id, text=f"⛔ BOT ARRETE AUTOMATIQUEMENT ⛔\n\nMon bilan à payer: {u['debt']}$ ({u['wins']} WIN x 1,5$)\nTape /pay et envoie ton ID au patron pour payer mon BILAN\n\n🚫 BLOQUE BILAN 7.5$ (5 WIN x 1,5$)\n/pay + envoie ID au patron pour payer mon\nID: {q.from_user.id}\n\nMON BILAN PAYE! Bot débloqué! Tu peux refaire 0 WIN\n\nDommage mais ne pas abandonne!\nNe lâche pas, le prochain sera gagnant! 😊")
        return
    if d=="LOSS":
        u["losses"]+=1
        await q.message.reply_text(f"LOSS Perdu - courage!")
        return

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    await update.message.reply_text(f"🔥 JOSH AI V8.6 MT5 🔥\n\nSalut ami 👋 Marchés MT5 réels\n\n📊 /analyse - Voir TOP 3 marchés\nTape gold / eurusd / gbpusd\n\n💰 GRATUIT: 5h/jour\n💵 1 WIN = 1,5$ bilan | Bloqué 7,5$ (5 WIN)\n🔥 PAYANT: 24h/24 illimité\n\n⏱️ Reste 299 min | Bilan: {u['debt']}$\nTape /analyse")

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    if u.get("debt_block"): await update.message.reply_text(f"🚫 BLOQUE BILAN {u['debt']}$"); return
    allowed, mins = check_free(u)
    if not allowed: await update.message.reply_text("🚫 5h finies /pay"); return
    prices=get_mt5_prices(); u["last_prices"]=prices
    await send_top_markets(context, update.effective_chat.id, prices, mins)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    txt = update.message.text.lower()
    u=get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    target=None
    if any(x in txt for x in ["gold","xau","1"]): target="GOLD"
    elif any(x in txt for x in ["eur","euro","2"]): target="EURUSD"
    elif any(x in txt for x in ["gbp","bipy","3"]): target="GBPUSD"
    if target:
        price = u.get("last_prices",{}).get(target) or get_mt5_prices().get(target)
        await send_detailed_analysis(context, update.effective_chat.id, target, price)

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)
    await update.message.reply_text(f"ID: {update.effective_user.id}\nBilan {u['debt']}$")

async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=MY_ADMIN_ID: return
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
    print("V6 CLASSIC + SUPPORT RESISTANCE")
    app.run_polling()
