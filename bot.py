# bot.py
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from auth_decorators import owner_only
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes,):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Bot started!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


#Force Buy Commands
from solana_monitor import send_alert
from bsc_monitor import send_bnb_alert


@owner_only
async def force_buy_sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force a simulated Solana token buy for testing"""
    chat_id = update.effective_chat.id

    # Check if we have enough arguments
    if len(context.args) >= 1:
        # Get the token address from arguments
        token_address = context.args[0]

        # Optionally get value
        value_sol = 1.5
        if len(context.args) >= 2:
            try:
                value_sol = float(context.args[1])
            except:
                pass

        # Create a test token
        test_token = {
            "address": token_address,
            "name": "Test Token",
            "symbol": "TEST",
            "group_id": chat_id
        }

        # Send a test alert

        success = await send_alert(
            bot=context.bot,
            token_info=test_token,
            chain="solana",
            value_token=value_sol,
            value_usd=value_sol * 100,  # Rough estimate for testing
            tx_hash="test_transaction_hash_123",
            dex_name="Raydium"
        )

        if success:
            await update.message.reply_text("✅ Test SOL buy alert sent successfully!")
        else:
            await update.message.reply_text("❌ Failed to send test alert")
    else:
        await update.message.reply_text("⚠️ Please provide a token address: /force_buy_sol <address> [value_sol]")

@owner_only
async def force_buy_bnb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test command to simulate a BNB token purchase alert"""
    try:
        chat_id = update.effective_chat.id
        token = "0x1234567890abcdef1234567890abcdef12345678" # Placeholder - replace with actual logic
        tx = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcdef" # Placeholder - replace with actual logic
        value_bnb = 1.2345
        value_usd = 638.00

        # Import and use BNBMonitor
        from bsc_monitor import BNBMonitor
        bnb = BNBMonitor.get_instance(context.bot)
        await bnb.send_alert(chat_id, token, tx, value_bnb, value_usd)

        await update.message.reply_text("✅ Test BNB alert sent!")
        logger.info(f"Sent test BNB alert to {chat_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending test alert: {str(e)}")
        logger.error(f"Error in force_buy_bnb: {e}")



def run_bot(token):
    application = ApplicationBuilder().token(token).build()

    start_handler = CommandHandler('start', start)
    echo_handler = CommandHandler('echo', echo)
    force_buy_sol_handler = CommandHandler('force_buy_sol', force_buy_sol)
    force_buy_bnb_handler = CommandHandler('force_buy_bnb', force_buy_bnb)

    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(force_buy_sol_handler)
    application.add_handler(force_buy_bnb_handler)

    application.run_polling()


# Example usage (replace with your actual token)
#run_bot("YOUR_BOT_TOKEN")

# Example of owner_only decorator
def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id == 1234567: # Replace with your user ID
            await func(update, context)
        else:
            await update.message.reply_text("You are not authorized to use this command.")

    return wrapper


#solana_monitor.py (example)
async def send_alert(bot, token_info, chain, value_token, value_usd, tx_hash, dex_name):
    try:
        #Your Solana alert logic here
        await bot.send_message(chat_id=token_info["group_id"], text=f"Solana alert: {token_info['name']} bought for {value_usd} USD")
        return True
    except Exception as e:
        print(f"Error sending Solana alert: {e}")
        return False

#bsc_monitor.py (example)
async def send_bnb_alert(bot, chat_id, symbol, amount, tx_hash, token_info, usd_value, dex_name):
    try:
        #Your BNB alert logic here
        await bot.send_message(chat_id=chat_id, text=f"BNB alert: {symbol} bought for {usd_value} USD")
        return True
    except Exception as e:
        print(f"Error sending BNB alert: {e}")
        return False