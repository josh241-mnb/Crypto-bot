import os, requests, logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")

def get_price(symbol: str):
    s = symbol.upper().strip()
    # Mapping spécial or
    if s in ["GOLD", "XAU", "XAAUD", "XAUUSD", "PAXG", "GOLDUSD"]:
        s = "PAXG"

    # 1. Essaie Binance
    try:
        binance_symbol = f"{s}USDT"
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
        r = requests.get(url, timeout=8).json()
        if "lastPrice" in r:
            return float(r["lastPrice"]), float(r["priceChangePercent"]), s
    except Exception as e:
        print(f"Binance fail {s}: {e}")

    # 2. Fallback CoinGecko (marche pour Gold via PAXG)
    try:
        coingecko_map = {"PAXG": "pax-gold", "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin"}
        cg_id = coingecko_map.get(s, s.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=8).json()
        if cg_id in r:
            price = float(r[cg_id]["usd"])
            change = float(r[cg_id].get("usd_24h_change", 0))
            return price, change, s
    except Exception as e:
        print(f"Coingecko fail {s}: {e}")

    return None, None, s

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 JOSH AI V3 en ligne bro!\nTeste: BTC, ETH, SOL, GOLD, XAAUD, BNB... tout marche!")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        if not text: return
        symbol = text.split()[0].replace("/","")

        price, change, name = get_price(symbol)
        if price is None:
            await update.message.reply_text(f"Je connais pas {symbol.upper()} bro, essaie BTC, ETH, SOL, GOLD")
            return

        emoji = "📈" if change >= 0 else "📉"
        await update.message.reply_text(f"{emoji} {name} = ${price:,.2f}\n24h: {change:+.2f}%")

    except Exception as e:
        print(f"handle error: {e}")
        await update.message.reply_text("Petite erreur bro, réessaie un symbole!")

if __name__ == "__main__":
    print("JOSH AI V3 STARTED")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.run_polling()
