import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")

# Dictionnaire complet - c'est ça qui manquait
SYMBOLS = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "XRP": "XRPUSDT", "DOGE": "DOGEUSDT",
    "ADA": "ADAUSDT", "SHIB": "SHIBUSDT", "AVAX": "AVAXUSDT",
    "GOLD": "PAXGUSDT", "XAU": "PAXGUSDT", "XAAUD": "PAXGUSDT", "XAUUSD": "PAXGUSDT",
    "PAXG": "PAXGUSDT", "XAG": "XAGUSDT", "SILVER": "XAGUSDT"
}

def get_price(symbol):
    try:
        coin = SYMBOLS.get(symbol.upper())
        if not coin:
            # Essaie direct sur Binance
            coin = f"{symbol.upper()}USDT"

        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={coin}"
        r = requests.get(url, timeout=5).json()

        if "lastPrice" in r:
            price = float(r["lastPrice"])
            change = float(r["priceChangePercent"])
            return price, change
        else:
            return None, None
    except Exception as e:
        print(f"Erreur prix {symbol}: {e}")
        return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 JOSH AI en ligne bro!\nEnvoie BTC, ETH, SOL, GOLD, XAU etc\nJe ne crash jamais maintenant!")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip().upper().replace("/", "")
        if not text:
            return

        # Prend le premier mot seulement
        symbol = text.split()[0]

        price, change = get_price(symbol)

        if price is None:
            await update.message.reply_text(f"Je connais pas {symbol} bro, essaie BTC, ETH, SOL, GOLD, BNB etc")
            return

        emoji = "📈" if change >= 0 else "📉"
        await update.message.reply_text(f"{emoji} {symbol} = ${price:,.2f}\n24h: {change:+.2f}%")

    except Exception as e:
        # CETTE PARTIE EMPECHE LE CRASH - c'est la clé!
        print(f"Erreur handle: {e}")
        try:
            await update.message.reply_text(f"Oups petite erreur sur {text} bro, réessaie!")
        except:
            pass

if __name__ == "__main__":
    print("JOSH AI STARTED - V2 ANTI-CRASH")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.run_polling()
