import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 JOSH AI en ligne bro !\nEnvoie BTC, ETH, SOL etc")

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.strip().lower()
    if coin.startswith("/"): return
    ids = {"btc":"bitcoin","eth":"ethereum","sol":"solana","doge":"dogecoin","pepe":"pepe","shib":"shiba-inu"}
    coin_id = ids.get(coin, coin)
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=10).json()
        if coin_id in r:
            price = r[coin_id]['usd']
            change = r[coin_id].get('usd_24h_change', 0)
            emoji = "📈" if change >= 0 else "📉"
            await update.message.reply_text(f"{emoji} {coin.upper()} = ${price}\n24h: {change:.2f}%")
        else:
            await update.message.reply_text(f"Je connais pas {coin.upper()} bro")
    except Exception as e:
        await update.message.reply_text(f"Erreur: {e}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_price))
print("JOSH AI STARTED")
app.run_polling()
