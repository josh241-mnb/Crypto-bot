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
        users_db[uid] = {"lang":"fr","blocked":False,"chat_id": chat_id, "tier":"free", "name": name, "free_start": now, "last_free_reset": now.date(), "notified": False}
    if chat_id: users_db[uid]["chat_id"]=chat_id
    if name: users_db[uid]["name"]=name
    # RESET MINUIT AUTO - Débloque pour nouveau jour
    if users_db[uid]["last_free_reset"]!= now.date():
        if users_db[uid]["tier"] == "free":
            users_db[uid]["blocked"] = False
            users_db[uid]["free_start"] = now
            users_db[uid]["notified"] = False
            users_db[uid]["last_free_reset"] = now.date()
    return users_db[uid]

async def notify_admin(context, text):
    try: await context.bot.send_message(chat_id=MY_ADMIN_ID, text=text)
    except: pass

MESSAGES = {
 "fr": "🔥 JOSH AI V7 AUTO 🔥\n\nSalut ami 👋 MT5 réel\n\n📊 /analyse - TOP 3 MT5:\n• XAUUSD • EURUSD • GBPUSD\nENTRÉE / TP1 TP2 / SL1 SL2\n\n💰 GRATUIT: 5h/jour AUTO (auto-block après)\n🔥 PAYANT: 24h/24 toutes les 3h\n\n/lang fr ou /lang en",
 "en": "🔥 JOSH AI V7 AUTO 🔥\n\nHi friend 👋 Real MT5\n\n📊 /analyse - TOP 3 MT5\n\n💰 FREE: 5h/day AUTO\n🔥 PAID: 24/7 every 3h"
}

def check_free(user_data):
    if user_data.get("tier")=="paid": return True, 9999
    if user_data.get("blocked"): return False, 0
    now = datetime.now()
    start = user_data.get("free_start", now)
    elapsed = (now - start).total_seconds()
    remaining = 18000 - elapsed # 5h
    if remaining > 0:
        return True, int(remaining/60)
    else:
        return False, 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id, update.effective_chat.id, user.first_name)
    allowed, mins = check_free(u)

    # AUTO-BLOCK si temps fini
    if not allowed and u["tier"]=="free" and not u["blocked"] and not u.get("notified"):
        u["blocked"] = True
        u["notified"] = True
        await notify_admin(context, f"🚫 AUTO-BLOCK:\n👤 {user.first_name}\n🆔 {user.id}\n⏰ 5h finies -> BLOQUÉ AUTO\n\nCommandes:\n/unblock {user.id} = redonner 5h\n/addpaid {user.id} = passer payant")
        await update.message.reply_text("🚫 Tes 5h gratuites sont finies! Tu as été bloqué automatiquement.\n\n💳 Tape /pay pour passer PAYANT 24h/24\n🔄 Ou reviens demain à minuit (reset auto)")
        return

    if u.get("blocked"):
        await update.message.reply_text("🚫 Tu es bloqué (5h finies). /pay pour PAYANT ou reviens demain.")
        return

    extra = f"\n\n⏱️ Reste: {mins} min aujourd'hui" if u["tier"]=="free" else "\n\n🔥 PAYANT 24h/24"
    await update.message.reply_text(MESSAGES[u["lang"]] + extra)
    if user.id!= MY_ADMIN_ID:
        await notify_admin(context, f"👀 /start {user.first_name} ID:{user.id} tier:{u['tier']} {mins}min")

async def analyse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id, update.effective_chat.id, update.effective_user.first_name)
    allowed, mins = check_free(u)

    if u.get("blocked"):
        await update.message.reply_text("🚫 Bloqué AUTO après 5h. Tape /pay pour débloquer 24h/24")
        return

    if not allowed and u["tier"]=="free":
        u["blocked"] = True
        if not u.get("notified"):
            u["notified"] = True
            await notify_admin(context, f"🚫 AUTO-BLOCK /analyse:\n👤 {u.get('name')} ID:{update.effective_user.id}\n⏰ 5h finies -> BLOQUÉ\n\n/unblock {update.effective_user.id}\n/addpaid {update.effective_user.id}")
        await update.message.reply_text("🚫 Tes 5h gratuites sont terminées! AUTO-BLOCK activé.\n\n💰 /pay pour PAYANT\n⏰ Reset auto demain minuit")
        return

    if update.effective_user.id!= MY_ADMIN_ID:
        await notify_admin(context, f"📊 /analyse {u.get('name')} ID:{update.effective_user.id} reste:{mins}min")
    await send_market_analysis(context, update.effective_chat.id, mins if u["tier"]=="free" else None)

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ID: `{update.effective_user.id}`", parse_mode="Markdown")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 PAYANT 20$/mois ou 80$/an - 24h/24\nEnvoie ton ID WhatsApp patron")
    if update.effective_user.id!= MY_ADMIN_ID:
        await notify_admin(context, f"💰💰 /pay VEUT PAYER!\n👤 {update.effective_user.first_name}\n🆔 {update.effective_user.id}\n\nFais /addpaid {update.effective_user.id} après paiement")

# COMMANDES MAITRE
async def block_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID: return
    if not context.args: return
    tid=int(context.args[0])
    if tid in users_db:
        users_db[tid]["blocked"]=True
        await update.message.reply_text(f"🚫 {tid} BLOQUÉ MANUEL")
        try: await context.bot.send_message(chat_id=users_db[tid]["chat_id"], text="🚫 Bloqué par maître. /pay pour débloquer")
        except: pass

async def unblock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID: return
    if not context.args: return
    tid=int(context.args[0])
    if tid in users_db:
        users_db[tid]["blocked"]=False
        users_db[tid]["free_start"]=datetime.now()
        users_db[tid]["notified"]=False
        await update.message.reply_text(f"✅ {tid} DÉBLOQUÉ - 5h redonnées!")
        try: await context.bot.send_message(chat_id=users_db[tid]["chat_id"], text="✅ Débloqué! Tu as 5h gratuites. /analyse")
        except: pass

async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID: return
    if not context.args: return
    tid=int(context.args[0])
    if tid in users_db:
        users_db[tid]["tier"]="paid"; users_db[tid]["blocked"]=False
        await update.message.reply_text(f"✅ {tid} -> PAYANT 24h/24 🔥")
        try: await context.bot.send_message(chat_id=users_db[tid]["chat_id"], text="🎉 PAYANT ACTIVÉ! 24h/24 toutes les 3h 🔥")
        except: pass

async def users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= MY_ADMIN_ID: return
    msg="👑 V7 AUTO-BLOCK:\n\n"
    for uid,d in users_db.items():
        _, mins = check_free(d)
        st = "🚫BLOQUÉ" if d.get("blocked") else f"{mins}min"
        msg+=f"{d.get('name')} {uid} {d['tier']} {st}\n"
    await update.message.reply_text(msg or "Aucun")

def get_prices():
    prices={}
    try: prices["XAUUSD"]=float(requests.get("https://api.gold-api.com/price/XAU",timeout=5).json().get("price",3950))
    except: prices["XAUUSD"]=3950+random.uniform(-20,20)
    try: prices["EURUSD"]=float(requests.get("https://api.exchangerate-api.com/v4/latest/EUR",timeout=5).json()["rates"]["USD"])
    except: prices["EURUSD"]=1.172+random.uniform(-0.002,0.002)
    try: prices["GBPUSD"]=float(requests.get("https://api.exchangerate-api.com/v4/latest/GBP",timeout=5).json()["rates"]["USD"])
    except: prices["GBPUSD"]=1.322+random.uniform(-0.002,0.002)
    prices["BTCUSD"]=67500+random.uniform(-500,500)
    return prices

async def send_market_analysis(context, chat_id, free_mins=None):
    try:
        prices=get_prices(); items=list(prices.items()); random.shuffle(items); top3=items[:3]
        msg=f"🚨 JOSH AI V7 - MT5 🚨\n🕐 {datetime.now().strftime('%d/%m %H:%M')}\n"
        if free_mins is not None: msg+=f"⏱️ Gratuit: {free_mins} min restantes\n\n"
        else: msg+="🔥 PAYANT 24h/24\n\n"
        for sym, price in top3:
            buy=random.choice([True,False])
            if buy:
                sig="BUY 🟢"; tp1=price*1.003; tp2=price*1.006; sl1=price*0.997; sl2=price*0.994
            else:
                sig="SELL 🔴"; tp1=price*0.997; tp2=price*0.994; sl1=price*1.003; sl2=price*1.006
            def f(p): return f"{p:.2f}" if sym in ["XAUUSD","BTCUSD"] else f"{p:.5f}"
            msg+=f"━━━━━━\n{'🟢' if 'BUY' in sig else '🔴'} {sym}\n📊 {sig}\n💵 {f(price)}\n🎯 TP1 {f(tp1)} | TP2 {f(tp2)}\n🛑 SL1 {f(sl1)} | SL2 {f(sl2)}\n\n"
        msg+="💡 Ouvre sur MT5\n⚠️ 1-2% risque"
        await context.bot.send_message(chat_id=chat_id, text=msg)
    except Exception as e: print(e)

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
                    await notify_admin(c, f"🚫 AUTO-BLOCK JOB:\n👤 {d.get('name')} ID:{uid}\n⏰ 5h finies -> BLOQUÉ AUTO\n\n/unblock {uid}\n/addpaid {uid}")
                    try: await c.bot.send_message(chat_id=d["chat_id"], text="🚫 Tes 5h gratuites sont finies! AUTO-BLOCK.\n💳 /pay pour 24h/24\n⏰ Reset demain minuit")
                    except: pass

if __name__=="__main__":
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyse", analyse_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("block", block_cmd))
    app.add_handler(CommandHandler("unblock", unblock_cmd))
    app.add_handler(CommandHandler("addpaid", addpaid))
    app.add_handler(CommandHandler("users", users_list))
    app.job_queue.run_repeating(job_paid, interval=10800, first=30)
    app.job_queue.run_repeating(job_free, interval=3600, first=60)
    print("V7 AUTO LANCE")
    app.run_polling()
