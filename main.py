
import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# Mapping que tu voulais
SYMBOLS = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "gold": "pax-gold", "xau": "pax-gold", "xauusd": "pax-gold", "xaaud": "pax-gold", "paxg": "pax-gold",
    "silver": "kinesis-silver", "xag": "kinesis-silver", "kag": "kinesis-silver",
    "sol": "solana", "bnb": "bnb", "xrp": "ripple", "doge": "dogecoin"
}

def get_price(coingecko_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=10).json()
        data = r.get(coingecko_id)
        if not data: return None
        price = data.get("usd")
        change = data.get("usd_24h_change", 0)
        return price, change
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Josh AI est en ligne 24h/24 bro!\nTape: Btc, Eth, Gold, Silver")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    coin_id = SYMBOLS.get(text)
    if not coin_id:
        await update.message.reply_text(f"Je connais pas {text} bro, essaie BTC, ETH, GOLD, SILVER")
        return
    result = get_price(coin_id)
    if not result:
        await update.message.reply_text("API en pause bro, réessaie 10 sec")
        return
    price, change = result
    emoji = "📈" if change >= 0 else "📉"
    await update.message.reply_text(f"{emoji} {text.upper()} = ${price:,.2f}\n24h: {change:+.2f}%")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("BOT_TOKEN manquant!")
        exit(1)
    print("Josh AI démarre 24h/24...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
