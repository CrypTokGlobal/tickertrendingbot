
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    MessageHandler, 
    filters,
    CallbackQueryHandler
)
from eth_monitor import get_instance as get_eth_monitor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define conversation states
TRACK_ADDRESS, TRACK_NAME, TRACK_SYMBOL, TRACK_MIN = range(4)
TRACK_SOL_ADDRESS, TRACK_SOL_NAME, TRACK_SOL_SYMBOL, TRACK_SOL_MIN = range(4, 8)

# Ethereum token tracking conversation
async def start_track_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the conversation flow for tracking an Ethereum token"""
    logger.info(f"Starting track flow for user {update.effective_user.id}")
    await update.message.reply_text(
        "📝 Let's set up tracking for your *Ethereum* token.\n\n"
        "Please send the contract address:",
        parse_mode="Markdown"
    )
    return TRACK_ADDRESS

async def receive_contract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the contract address"""
    context.user_data["address"] = update.message.text.strip()
    logger.info(f"Received ETH contract address: {context.user_data['address']}")
    await update.message.reply_text(
        "🆔 Got it!\n\nNow send the token name (e.g., Uniswap):"
    )
    return TRACK_NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the token name"""
    context.user_data["name"] = update.message.text.strip()
    logger.info(f"Received token name: {context.user_data['name']}")
    await update.message.reply_text(
        "🔤 Now send the token symbol (e.g., UNI):"
    )
    return TRACK_SYMBOL

async def receive_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the token symbol"""
    context.user_data["symbol"] = update.message.text.strip()
    logger.info(f"Received token symbol: {context.user_data['symbol']}")
    await update.message.reply_text(
        "💵 (Optional) Enter a minimum USD alert value, or type 'skip':"
    )
    return TRACK_MIN

async def receive_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the minimum USD value and complete the token tracking setup"""
    value = update.message.text.strip()
    
    if value.lower() == 'skip':
        min_usd = 10.0  # Default value
    else:
        try:
            min_usd = float(value) if value.replace(".", "", 1).isdigit() else 10.0
        except ValueError:
            min_usd = 10.0
    
    context.user_data["min_usd"] = min_usd
    logger.info(f"Received minimum USD value: {min_usd}")

    # Track the token now
    monitor = get_eth_monitor(context.bot)
    address = context.user_data["address"]
    name = context.user_data["name"]
    symbol = context.user_data["symbol"]
    chat_id = update.effective_chat.id

    if monitor:
        try:
            monitor.track_contract(address, name, symbol, chat_id, min_usd)
            
            # Create chart button
            etherscan_url = f"https://etherscan.io/token/{address}"
            dextools_url = f"https://www.dextools.io/app/ether/pair-explorer/{address}"
            keyboard = [
                [
                    InlineKeyboardButton("📊 View Chart", url=dextools_url),
                    InlineKeyboardButton("🔍 Etherscan", url=etherscan_url)
                ],
                [
                    InlineKeyboardButton("🧪 Test Alert", callback_data=f"test_alert_{address}"),
                    InlineKeyboardButton("✨ Customize", callback_data=f"customize_{address}")
                ]
            ]

            await update.message.reply_text(
                f"✅ Now tracking *{name}* (*{symbol}*) on Ethereum\n\n"
                f"📋 *Details:*\n"
                f"• Address: `{address}`\n"
                f"• Minimum alert value: ${min_usd}\n"
                f"• Tracking in: This chat\n\n"
                f"🔔 You'll receive alerts for buy transactions on Ethereum DEXes",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error tracking token: {str(e)}")
    else:
        await update.message.reply_text("❌ Ethereum monitor not initialized. Please try again later.")
    
    return ConversationHandler.END

# Solana token tracking conversation
async def start_tracksol_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the conversation flow for tracking a Solana token"""
    logger.info(f"Starting tracksol flow for user {update.effective_user.id}")
    await update.message.reply_text(
        "📝 Let's set up tracking for your *Solana* token.\n\n"
        "Please send the token address:",
        parse_mode="Markdown"
    )
    return TRACK_SOL_ADDRESS

async def receive_sol_contract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the Solana contract address"""
    context.user_data["sol_address"] = update.message.text.strip()
    logger.info(f"Received SOL token address: {context.user_data['sol_address']}")
    await update.message.reply_text(
        "🆔 Got it!\n\nNow send the token name (e.g., Solana):"
    )
    return TRACK_SOL_NAME

async def receive_sol_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the Solana token name"""
    context.user_data["sol_name"] = update.message.text.strip()
    logger.info(f"Received token name: {context.user_data['sol_name']}")
    await update.message.reply_text(
        "🔤 Now send the token symbol (e.g., SOL):"
    )
    return TRACK_SOL_SYMBOL

async def receive_sol_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the Solana token symbol"""
    context.user_data["sol_symbol"] = update.message.text.strip()
    logger.info(f"Received token symbol: {context.user_data['sol_symbol']}")
    await update.message.reply_text(
        "💵 (Optional) Enter a minimum USD alert value, or type 'skip':"
    )
    return TRACK_SOL_MIN

async def receive_sol_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the minimum USD value and complete the Solana token tracking setup"""
    value = update.message.text.strip()
    
    if value.lower() == 'skip':
        min_usd = 10.0  # Default value
    else:
        try:
            min_usd = float(value) if value.replace(".", "", 1).isdigit() else 10.0
        except ValueError:
            min_usd = 10.0
    
    context.user_data["sol_min_usd"] = min_usd
    logger.info(f"Received minimum USD value: {min_usd}")

    # Track the Solana token now
    from solana_monitor import SolanaMonitor
    address = context.user_data["sol_address"]
    name = context.user_data["sol_name"]
    symbol = context.user_data["sol_symbol"]
    chat_id = update.effective_chat.id

    # Get the global SolanaMonitor instance
    global_symbols = globals()
    sol_monitor = global_symbols.get('sol_monitor')
    
    if sol_monitor:
        try:
            sol_monitor.add_token(address, name, symbol, chat_id, min_value_usd=min_usd)
            
            # Create chart button
            chart_url = f"https://dexscreener.com/solana/{address}"
            pump_url = f"https://pump.fun/token/{address}"
            keyboard = [
                [
                    InlineKeyboardButton("📊 View Chart", url=chart_url),
                    InlineKeyboardButton("🎯 Pump.fun", url=pump_url)
                ],
                [
                    InlineKeyboardButton("🧪 Test Alert", callback_data=f"test_alert_sol_{address}"),
                    InlineKeyboardButton("✨ Customize", callback_data=f"customize_{address}")
                ]
            ]

            await update.message.reply_text(
                f"✅ Now tracking *{name}* (*{symbol}*) on Solana\n\n"
                f"📋 *Details:*\n"
                f"• Address: `{address}`\n"
                f"• Minimum alert value: ${min_usd}\n"
                f"• Tracking in: This chat\n\n"
                f"🔔 You'll receive alerts for buys on Solana DEXes and Pump.fun",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Optional: Check if token has data available
            import asyncio
            asyncio.create_task(sol_monitor.check_token_activity(address, {
                "address": address,
                "name": name,
                "symbol": symbol
            }))
        except Exception as e:
            await update.message.reply_text(f"❌ Error tracking token: {str(e)}")
    else:
        await update.message.reply_text("❌ Solana monitor not initialized. Please try again later.")
    
    return ConversationHandler.END

async def cancel_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation"""
    await update.message.reply_text("❌ Tracking setup cancelled.")
    return ConversationHandler.END

# Button callback to start tracking flows
async def track_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle track button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "track_eth_flow":
        await query.message.reply_text("📝 Let's set up tracking for your *Ethereum* token.\n\nPlease send the contract address:", parse_mode="Markdown")
        return TRACK_ADDRESS
    elif query.data == "track_sol_flow":
        await query.message.reply_text("📝 Let's set up tracking for your *Solana* token.\n\nPlease send the token address:", parse_mode="Markdown")
        return TRACK_SOL_ADDRESS
    return ConversationHandler.END

def get_conversation_handlers():
    """Return all conversation handlers"""
    eth_track_handler = ConversationHandler(
        entry_points=[
            CommandHandler("track_step", start_track_flow),
            CallbackQueryHandler(track_button_callback, pattern="^track_eth_flow$")
        ],
        states={
            TRACK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_contract)],
            TRACK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            TRACK_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_symbol)],
            TRACK_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_min)],
        },
        fallbacks=[CommandHandler("cancel", cancel_track)]
    )
    
    sol_track_handler = ConversationHandler(
        entry_points=[
            CommandHandler("tracksol_step", start_tracksol_flow),
            CallbackQueryHandler(track_button_callback, pattern="^track_sol_flow$")
        ],
        states={
            TRACK_SOL_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sol_contract)],
            TRACK_SOL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sol_name)],
            TRACK_SOL_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sol_symbol)],
            TRACK_SOL_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sol_min)],
        },
        fallbacks=[CommandHandler("cancel", cancel_track)]
    )
    
    return [eth_track_handler, sol_track_handler]


async def handle_track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced handler for the /track command to track Ethereum tokens"""
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) < 3:
        await update.message.reply_text(
            "❗ Usage: `/track <contract_address> <token_name> <token_symbol>`\n\n"
            "Example:\n`/track 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 Uniswap UNI`",
            parse_mode="Markdown"
        )
        return

    contract_address = args[0].strip()
    name = args[1].strip()
    symbol = args[2].strip()
    
    # Get min_volume if provided, otherwise default to 0
    min_volume_usd = float(args[3]) if len(args) > 3 and args[3].replace(".", "", 1).isdigit() else 0

    # Validate Ethereum address format
    if not contract_address.startswith("0x") or len(contract_address) != 42:
        await update.message.reply_text(
            "❌ Invalid Ethereum address format. Address should start with 0x and be 42 characters long.",
            parse_mode="Markdown"
        )
        return

    try:
        from data_manager import add_tracked_token
        from eth_monitor import get_instance as get_eth_monitor
        
        # Add to data manager
        success = add_tracked_token(chat_id, contract_address, name, symbol, min_volume_usd, network="ethereum")
        
        # Also register with ETH monitor
        eth_monitor = get_eth_monitor(context.bot)
        if eth_monitor:
            eth_monitor.track_contract(contract_address, name, symbol, chat_id, min_volume_usd)
        
        if success:
            # Create buttons for chart and more actions
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            etherscan_url = f"https://etherscan.io/token/{contract_address}"
            dextools_url = f"https://www.dextools.io/app/ether/pair-explorer/{contract_address}"
            keyboard = [
                [
                    InlineKeyboardButton("📊 View Chart", url=dextools_url),
                    InlineKeyboardButton("🔍 Etherscan", url=etherscan_url)
                ],
                [
                    InlineKeyboardButton("🧪 Test Alert", callback_data=f"test_alert_{contract_address}"),
                    InlineKeyboardButton("✨ Customize", callback_data=f"customize_{contract_address}")
                ]
            ]

            await update.message.reply_text(
                f"✅ Now tracking *{name}* (*{symbol}*) on Ethereum\n\n"
                f"📋 *Details:*\n"
                f"• Address: `{contract_address}`\n"
                f"• Minimum alert value: ${min_volume_usd}\n"
                f"• Tracking in: This chat\n\n"
                f"🔔 You'll receive alerts for buy transactions on Ethereum DEXes",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text("⚠️ Something went wrong when tracking the token. Please try again.")
    except Exception as e:
        logger.error(f"Error in track command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
