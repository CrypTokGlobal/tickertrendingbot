import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

# Set up logging
logger = logging.getLogger(__name__)

import json
import logging
import os.path
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from telegram.constants import ParseMode

async def verify_eth_transaction(tx_hash, expected_amount, wallet_address):
    """Verify an Ethereum transaction using PaymentHandler"""
    from payment_handler import get_payment_handler
    handler = get_payment_handler()
    success, message, tx_data = handler.verify_eth_transaction(
        tx_hash=tx_hash, 
        expected_amount=expected_amount, 
        target_address=wallet_address
    )
    return success, message

async def verify_sol_transaction(tx_signature, expected_amount, wallet_address):
    """Verify a Solana transaction using PaymentHandler"""
    from payment_handler import get_payment_handler
    handler = get_payment_handler()
    success, message, tx_data = handler.verify_solana_transaction(
        tx_hash=tx_signature, 
        expected_amount=expected_amount, 
        target_address=wallet_address
    )
    return success, message

# Setup logging
logger = logging.getLogger(__name__)

# States for the conversation
CHOOSING_NETWORK, SELECTING_PACKAGE, SELECTING_TOKEN, ENTERING_CHAT_LINK, ENTERING_EMOJIS, CONFIRMING_PAYMENT = range(6)

# Callback data patterns
BOOST_MENU = "boost_menu"
HOW_BOOST_WORKS = "how_boost_works"
NETWORK_SOL = "network_sol"
NETWORK_ETH = "network_eth"
PACKAGE_SELECT = "package_select"
BACK_TO_MENU = "back_to_menu"
BACK_TO_NETWORKS = "back_to_networks"
PAYMENT_CONFIRM = "payment_confirm"
SKIP_EMOJIS = "skip_emojis"

# Load boost configuration
def load_boost_config():
    try:
        if os.path.exists("boost_config.json"):
            with open("boost_config.json", "r") as f:
                return json.load(f)
        else:
            # Fallback default config with updated pricing
            return {
                "solana": {
                    "3h": {"price": 0.40, "label": "🕒 3 Hours - Quick Boost", "hours": 3},
                    "6h": {"price": 0.75, "label": "⏱ 6 Hours - Medium Boost", "hours": 6},
                    "12h": {"price": 1.00, "label": "🌗 12 Hours - Half Day", "hours": 12},
                    "24h": {"price": 2.00, "label": "📆 24 Hours - Full Day", "hours": 24},
                    "48h": {"price": 3.00, "label": "🚀 48 Hours - Extended", "hours": 48}
                },
                "ethereum": {
                    "1h": {"price": 0.05, "label": "⏰ 1 Hour - Quick Boost", "hours": 1},
                    "6h": {"price": 0.12, "label": "⌛ 6 Hours - Medium Boost", "hours": 6},
                    "24h": {"price": 0.25, "label": "🗓 24 Hours - Full Day", "hours": 24},
                    "48h": {"price": 0.35, "label": "🧨 48 Hours - Extended", "hours": 48}
                },
                "wallet_addresses": {
                    "solana": "DbqdUJmaPgLKkCEhebokxGTuXhzoS7D2SuWxhahi8BYn",
                    "ethereum": "0x247cd53A34b1746C11944851247D7Dd802C1d703"
                }
            }
    except Exception as e:
        logger.error(f"Error loading boost config: {e}")
        return {}

# Global config
BOOST_CONFIG = load_boost_config()


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

def get_boost_chain_menu():
    keyboard = [
        [InlineKeyboardButton("🔵 Ethereum", callback_data="boost_select|eth")],
        [InlineKeyboardButton("🟠 Solana", callback_data="boost_select|sol")],
        [InlineKeyboardButton("🟡 BNB", callback_data="boost_select|bnb")],
        [InlineKeyboardButton("🟢 Base", callback_data="boost_select|base")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_boost_package_markup(chain: str):
    packages = BOOST_CONFIG.get(chain, {})
    keyboard = []
    for duration, data in packages.items():
        keyboard.append([InlineKeyboardButton(data["label"], callback_data=f"boostpkg|{chain[:3]}|{data['hours']}")])
    keyboard.append([InlineKeyboardButton("« Back", callback_data="boost_back")])
    return InlineKeyboardMarkup(keyboard)


def get_boost_duration_menu(chain: str):
    packages = {
        "ethereum": [
            ("⏰ 3 Hours – 0.05 ETH", "3"),
            ("⚡ 6 Hours – 0.08 ETH", "6"),
            ("🔥 12 Hours – 0.15 ETH", "12"),
            ("📅 24 Hours – 0.20 ETH", "24"),
            ("🚀 48 Hours – 0.30 ETH", "48"),
        ],
        "solana": [
            ("🕒 3 Hours – 0.40 SOL", "3"),
            ("⏱ 6 Hours – 0.75 SOL", "6"),
            ("🌗 12 Hours – 1.00 SOL", "12"),
            ("📅 24 Hours – 2.00 SOL", "24"),
            ("🚀 48 Hours – 3.00 SOL", "48"),
        ],
        "bnb": [
            ("⏰ 3 Hours – 0.10 BNB", "3"),
            ("⚡ 6 Hours – 0.18 BNB", "6"),
            ("🔥 12 Hours – 0.30 BNB", "12"),
            ("📅 24 Hours – 0.50 BNB", "24"),
            ("🚀 48 Hours – 0.80 BNB", "48"),
        ],
        "base": [
            ("⏰ 3 Hours – 0.05 BASE", "3"),
            ("⚡ 6 Hours – 0.08 BASE", "6"),
            ("🔥 12 Hours – 0.15 BASE", "12"),
            ("📅 24 Hours – 0.20 BASE", "24"),
            ("🚀 48 Hours – 0.30 BASE", "48"),
        ]
    }

    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"boost_duration|{chain}|{hours}")]
        for label, hours in packages.get(chain, packages["ethereum"])
    ]
    keyboard.append([InlineKeyboardButton("« Back", callback_data="boost_back")])
    return InlineKeyboardMarkup(keyboard)

async def handle_boost_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button in boost menu"""
    query = update.callback_query
    await query.answer()

    try:
        # Go back to boost selection menu
        keyboard = [
            [
                InlineKeyboardButton("🟣 Boost Ethereum Token", callback_data="network_eth"),
                InlineKeyboardButton("🔵 Boost Solana Token", callback_data="network_sol"),
            ],
            [
                InlineKeyboardButton("🟡 Boost BNB Token", callback_data="network_bnb"),
                InlineKeyboardButton("🟢 Boost Base Token", callback_data="network_base"),
            ],
            [
                InlineKeyboardButton("ℹ️ How Boost Works", callback_data="how_boost_works"),
            ],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="help_menu")]
        ]

        boost_text = (
            "🚀 <b>Boost Your Token's Visibility</b>\n\n"
            "Supercharge your token's reach by boosting it to our partner channels and communities.\n\n"
            "• <b>Increased Exposure</b> across multiple channels\n"
            "• <b>Higher Visibility</b> to potential buyers\n"
            "• <b>Professional Presentation</b> with your branding\n\n"
            "Select which blockchain your token is on:"
        )

        await query.edit_message_text(
            text=boost_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error handling boost back button: {e}")

        # If edit fails, send a new message
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=boost_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        logger.error(f"Error handling boost back button: {e}")

        # If edit fails, send a new message
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Let's go back to the main menu.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Main Menu", callback_data="help_menu")
                ]])
            )
        logger.error(f"Error handling boost back button: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ There was an error. Let's restart the boost process.",
                parse_mode="HTML"
            )
            # Call the boost selection handler again
            await handle_boost_selection(update, context)

def get_boost_button_markup():
    """Return a button that links to the boost menu"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Boost Your Project", callback_data="boost")]])

def get_rotating_links_markup(links):
    """Return a button for promoted projects"""
    if not links:
        return None

    # Use the most recent link
    latest_link = links[-1]
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔥 Promoted Project", url=latest_link)]])

async def handle_boost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /boost command to show network options"""
    keyboard = [
        [
            InlineKeyboardButton("🟣 Ethereum", callback_data="network_eth"),
            InlineKeyboardButton("🔵 Solana", callback_data="network_sol")
        ],
        [
            InlineKeyboardButton("🟡 BNB", callback_data="network_bnb"),
            InlineKeyboardButton("🟢 Base", callback_data="network_base")
        ],
        [
            InlineKeyboardButton("ℹ️ How Boosting Works", callback_data="how_boost_works")
        ],
        [InlineKeyboardButton("« Back", callback_data="help_menu")]
    ]

    boost_text = (
        "🚀 <b>Token Boost Packages</b>\n\n"
        "Boost your token to appear on the trending page and across our partner channels.\n\n"
        "• <b>Increased Visibility</b> to potential investors\n"
        "• <b>Higher Ranking</b> in alerts and notifications\n"
        "• <b>Professional Presentation</b> with your branding\n\n"
        "Select which blockchain your token is on:"
    )

    await update.message.reply_text(
        boost_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def handle_boost_chain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the network selection callback"""
    query = update.callback_query
    await query.answer()
    chain = query.data.split("|")[1]
    await query.edit_message_text(
        f"🚀 *Select Your {chain.upper()} Boost Package*\n\nChoose how long you want your project to be promoted:",
        reply_markup=get_boost_package_markup(chain),
        parse_mode='Markdown'
    )

async def handle_boost_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the back button to return to network selection"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚀 *Token Boost Packages*\nBoost your token to appear on the trending page.\n\nSelect your chain to begin:",
        reply_markup=get_boost_chain_menu(),
        parse_mode='Markdown'
    )

async def handle_boost_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the duration selection"""
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|")
    chain = parts[1]
    duration = parts[2]

    # Store the selected chain and duration in user_data for later use
    context.user_data["boost_chain"] = chain
    context.user_data["boost_duration"] = duration

    # Determine the wallet address based on chain
    wallets = {
        "ethereum": "0x247cd53A34b1746C11944851247D7Dd802C1d703",
        "solana": "DbqdUJmaPgLKkCEhebokxGTuXhzoS7D2SuWxhahi8BYn",
        "bnb": "0x247cd53A34b1746C11944851247D7Dd802C1d703",  # Use same as ETH for now
        "base": "0x247cd53A34b1746C11944851247D7Dd802C1d703" # Use same as ETH for now
    }

    wallet = wallets.get(chain, wallets["ethereum"])

    # Determine price based on chain and duration
    prices = {
        "ethereum": {"3": "0.05 ETH", "6": "0.08 ETH", "12": "0.15 ETH", "24": "0.20 ETH", "48": "0.30 ETH"},
        "solana": {"3": "0.40 SOL", "6": "0.75 SOL", "12": "1.00 SOL", "24": "2.00 SOL", "48": "3.00 SOL"},
        "bnb": {"3": "0.10 BNB", "6": "0.18 BNB", "12": "0.30 BNB", "24": "0.50 BNB", "48": "0.80 BNB"},
        "base": {"3": "0.05 BASE", "6": "0.08 BASE", "12": "0.15 BASE", "24": "0.20 BASE", "48": "0.30 BASE"}
    }

    price = prices.get(chain, {}).get(duration, "")

    await query.edit_message_text(
        f"✅ You selected {duration} hours boost on {chain.upper()}.\n\n"
        f"💰 Payment Amount: *{price}*\n\n"
        f"💳 Wallet Address:\n`{wallet}`\n\n"
        f"📩 After sending payment, reply with your transaction hash and the Telegram link you want to promote using:\n\n"
        f"`/boost_token {chain} <token_address> {duration} <tx_hash> <t.me/yourproject>`",
        parse_mode='Markdown'
    )

async def handle_boost_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle boost selection callbacks"""
    query = update.callback_query
    await query.answer()

    # Process the callback data
    data = query.data

    if data.startswith("boost_select|"):
        # Handle chain selection
        chain = data.split("|")[1]
        await query.edit_message_text(
            f"🚀 *Select Your {chain.upper()} Boost Package*\n\nChoose how long you want your project to be promoted:",
            reply_markup=get_boost_package_markup(chain),
            parse_mode='Markdown'
        )
    elif data == "boost_back":
        # Handle back button
        await query.edit_message_text(
            "🚀 *Token Boost Packages*\nBoost your token to appear on the trending page.\n\nSelect your chain to begin:",
            reply_markup=get_boost_chain_menu(),
            parse_mode='Markdown'
        )
    elif data.startswith("boostpkg|"):
        # Handle package selection
        parts = data.split("|")
        chain_code = parts[1]
        duration = parts[2]

        # Map chain codes to full names
        chain_mapping = {
            "eth": "ethereum",
            "sol": "solana",
            "bnb": "bnb",
            "base": "base"
        }

        chain = chain_mapping.get(chain_code, "ethereum")

        # Determine wallet address
        wallets = {
            "ethereum": "0x247cd53A34b1746C11944851247D7Dd802C1d703",
            "solana": "DbqdUJmaPgLKkCEhebokxGTuXhzoS7D2SuWxhahi8BYn",
            "bnb": "0x247cd53A34b1746C11944851247D7Dd802C1d703",  # Using ETH wallet for now
            "base": "0x247cd53A34b1746C11944851247D7Dd802C1d703" # Using ETH wallet for now
        }

        wallet = wallets.get(chain, wallets["ethereum"])

        # Pricing mappings
        prices = {
            "ethereum": {"3": "0.05 ETH", "6": "0.08 ETH", "12": "0.15 ETH", "24": "0.20 ETH", "48": "0.30 ETH"},
            "solana": {"3": "0.40 SOL", "6": "0.75 SOL", "12": "1.00 SOL", "24": "2.00 SOL", "48": "3.00 SOL"},
            "bnb": {"3": "0.10 BNB", "6": "0.18 BNB", "12": "0.30 BNB", "24": "0.50 BNB", "48": "0.80 BNB"},
            "base": {"3": "0.05 BASE", "6": "0.08 BASE", "12": "0.15 BASE", "24": "0.20 BASE", "48": "0.30 BASE"}
        }

        currency = "ETH" if chain == "ethereum" else "SOL" if chain == "solana" else "BNB" if chain == "bnb" else "BASE"
        price = prices.get(chain, {}).get(duration, "unknown")

        await query.edit_message_text(
            f"✅ *BOOST PACKAGE SELECTED*\n\n"
            f"• Chain: {chain.upper()}\n"
            f"• Duration: {duration} hours\n"
            f"• Payment: *{price}*\n\n"
            f"💳 *Payment Address:*\n`{wallet}`\n\n"
            f"📲 *After sending {price}, use this command:*\n\n"
            f"`/boost_token {chain} <token_address> {duration} <tx_hash> <t.me/yourproject>`\n\n"
            f"Our team will verify your payment and activate your boost immediately!",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Chains", callback_data="boost_back")]])
        )
    elif data.startswith("boost_duration|"):
        # For backward compatibility - handle old style duration selection
        parts = data.split("|")
        chain = parts[1]
        duration = parts[2]

        # Determine wallet and price
        wallets = {
            "ethereum": "0x247cd53A34b1746C11944851247D7Dd802C1d703",
            "solana": "DbqdUJmaPgLKkCEhebokxGTuXhzoS7D2SuWxhahi8BYn",
            "bnb": "0x247cd53A34b1746C11944851247D7Dd802C1d703",  # Using ETH wallet for now
            "base": "0x247cd53A34b1746C11944851247D7Dd802C1d703" # Using ETH wallet for now
        }

        wallet = wallets.get(chain, wallets["ethereum"])

        # Pricing mappings
        prices = {
            "ethereum": {"3": "0.05 ETH", "6": "0.08 ETH", "12": "0.15 ETH", "24": "0.20 ETH", "48": "0.30 ETH"},
            "solana": {"3": "0.40 SOL", "6": "0.75 SOL", "12": "1.00 SOL", "24": "2.00 SOL", "48": "3.00 SOL"},
            "bnb": {"3": "0.10 BNB", "6": "0.18 BNB", "12": "0.30 BNB", "24": "0.50 BNB", "48": "0.80 BNB"},
            "base": {"3": "0.05 BASE", "6": "0.08 BASE", "12": "0.15 BASE", "24": "0.20 BASE", "48": "0.30 BASE"}
        }

        price = prices.get(chain, {}).get(duration, "unknown")

        await query.edit_message_text(
            f"✅ You selected {duration} hours boost on {chain.upper()}.\n\n"
            f"💰 Payment Amount: *{price}*\n\n"
            f"💳 Wallet Address:\n`{wallet}`\n\n"
            f"📩 After sending payment, reply with your transaction hash and the Telegram link you want to promote using:\n\n"
            f"`/boost_token {chain} <token_address> {duration} <tx_hash> <t.me/yourproject>`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Chains", callback_data="boost_back")]])
        )
    elif data == "boost":
        # Handle the main boost button click
        await query.message.reply_text(
            "🚀 *Token Boost Packages*\nBoost your token to appear on the trending page.\n\nSelect your chain to begin:",
            reply_markup=get_boost_chain_menu(),
            parse_mode='Markdown'
        )

async def handle_boost_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the boost button click"""
    query = update.callback_query
    await query.answer()

    # Show the boost menu
    await query.message.reply_text(
        "🚀 *Token Boost Packages*\nBoost your token to appear on the trending page.\n\nSelect your chain to begin:",
        reply_markup=get_boost_chain_menu(),
        parse_mode='Markdown'
    )

def get_boost_handlers():
    """Return boost-related command handlers"""
    return [
        CommandHandler("boost", handle_boost_command),
        CallbackQueryHandler(handle_boost_chain, pattern=r'^boost_select\|'),
        CallbackQueryHandler(handle_boost_back, pattern=r'^boost_back$'),
        CallbackQueryHandler(handle_boost_duration, pattern=r'^boost_duration\|'),
        CallbackQueryHandler(handle_boost_selection, pattern=r'^boost$|boostpkg\|'),
        CallbackQueryHandler(handle_network_eth_callback, pattern=r'^network_eth$'),
        CallbackQueryHandler(handle_network_sol_callback, pattern=r'^network_sol$'),
        CallbackQueryHandler(handle_network_bnb_callback, pattern=r'^network_bnb$'),
        CallbackQueryHandler(handle_network_base_callback, pattern=r'^network_base$'),
        CallbackQueryHandler(handle_boost_token_callback, pattern=r'^boost$'), # Added handler for initial boost button
        CallbackQueryHandler(show_how_boost_works, pattern=r'^how_boost_works$')
    ]
async def show_how_boost_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show information about how token boosting works"""
    query = update.callback_query
    await query.answer()

    help_text = (
        "🚀 <b>How Token Boosting Works</b>\n\n"
        "Boosting increases your token's visibility across multiple channels:\n\n"
        "• Your token is promoted to our network of <b>partner channels</b>\n"
        "• Your project receives <b>priority placement</b> in alerts\n"
        "• Custom branding appears with all mentions of your token\n"
        "• Increased exposure to potential investors\n\n"
        "After payment confirmation, your boost activates immediately and runs for your selected duration."
    )

    keyboard = [[InlineKeyboardButton("« Back", callback_data="boost_back")]]

    try:
        await query.edit_message_text(
            text=help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error showing boost info: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=help_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

async def handle_boost_token_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle boost project button click"""
    query = update.callback_query
    await query.answer()

    # Create a rich UI for boosting - designed to match the screenshot with all 4 networks
    keyboard = [
        [
            InlineKeyboardButton("🟣 Ethereum", callback_data="network_eth"),
            InlineKeyboardButton("🔵 Solana", callback_data="network_sol")
        ],
        [
            InlineKeyboardButton("🟡 BNB", callback_data="network_bnb"),
            InlineKeyboardButton("🟢 Base", callback_data="network_base")
        ],
        [
            InlineKeyboardButton("ℹ️ How Boosting Works", callback_data="how_boost_works")
        ],
        [InlineKeyboardButton("« Back", callback_data="help_menu")]
    ]

    boost_text = (
        "🚀 <b>Token Boost Packages</b>\n\n"
        "Boost your token to appear on the trending page and across our partner channels.\n\n"
        "• <b>Increased Visibility</b> to potential investors\n"
        "• <b>Higher Ranking</b> in alerts and notifications\n"
        "• <b>Professional Presentation</b> with your branding\n\n"
        "Select which blockchain your token is on:"
    )

    await query.edit_message_text(
        text=boost_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def handle_network_bnb_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle BNB boost network selection"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("⏰ 3 Hours – 0.10 BNB", callback_data="boost_duration|bnb|3")],
        [InlineKeyboardButton("⚡ 6 Hours – 0.18 BNB", callback_data="boost_duration|bnb|6")],
        [InlineKeyboardButton("🔥 12 Hours – 0.30 BNB", callback_data="boost_duration|bnb|12")],
        [InlineKeyboardButton("📅 24 Hours – 0.50 BNB", callback_data="boost_duration|bnb|24")],
        [InlineKeyboardButton("🚀 48 Hours – 0.80 BNB", callback_data="boost_duration|bnb|48")],
        [InlineKeyboardButton("« Back", callback_data="boost_back")]
    ]

    await query.edit_message_text(
        "📋 Select your boost slot for BNB promotions:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def handle_network_eth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Ethereum boost network selection"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("⏰ 3 Hours – 0.05 ETH", callback_data="boost_duration|ethereum|3")],
        [InlineKeyboardButton("⚡ 6 Hours – 0.08 ETH", callback_data="boost_duration|ethereum|6")],
        [InlineKeyboardButton("🔥 12 Hours – 0.15 ETH", callback_data="boost_duration|ethereum|12")],
        [InlineKeyboardButton("📅 24 Hours – 0.20 ETH", callback_data="boost_duration|ethereum|24")],
        [InlineKeyboardButton("🚀 48 Hours – 0.30 ETH", callback_data="boost_duration|ethereum|48")],
        [InlineKeyboardButton("« Back", callback_data="boost_back")]
    ]

    await query.edit_message_text(
        "📋 Select your boost slot for ETH promotions:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def handle_network_sol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Solana boost network selection"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🕒 3 Hours – 0.40 SOL", callback_data="boost_duration|solana|3")],
        [InlineKeyboardButton("⏱ 6 Hours – 0.75 SOL", callback_data="boost_duration|solana|6")],
        [InlineKeyboardButton("🌗 12 Hours – 1.00 SOL", callback_data="boost_duration|solana|12")],
        [InlineKeyboardButton("📅 24 Hours – 2.00 SOL", callback_data="boost_duration|solana|24")],
        [InlineKeyboardButton("🚀 48 Hours – 3.00 SOL", callback_data="boost_duration|solana|48")],
        [InlineKeyboardButton("« Back", callback_data="boost_back")]
    ]

    await query.edit_message_text(
        "📋 Select your boost slot for SOL promotions:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def handle_network_base_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Base boost network selection"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("⏰ 3 Hours – 0.05 BASE", callback_data="boost_duration|base|3")],
        [InlineKeyboardButton("⚡ 6 Hours – 0.08 BASE", callback_data="boost_duration|base|6")],
        [InlineKeyboardButton("🔥 12 Hours – 0.15 BASE", callback_data="boost_duration|base|12")],
        [InlineKeyboardButton("📅 24 Hours – 0.20 BASE", callback_data="boost_duration|base|24")],
        [InlineKeyboardButton("🚀 48 Hours – 0.30 BASE", callback_data="boost_duration|base|48")],
        [InlineKeyboardButton("« Back", callback_data="boost_back")]
    ]

    await query.edit_message_text(
        "📋 Select your boost slot for BASE promotions:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


def get_boost_handlers():
    """Return boost-related command handlers"""
    return [
        CommandHandler("boost", handle_boost_command),
        CallbackQueryHandler(handle_boost_chain, pattern=r'^boost_select\|'),
        CallbackQueryHandler(handle_boost_back, pattern=r'^boost_back$'),
        CallbackQueryHandler(handle_boost_duration, pattern=r'^boost_duration\|'),
        CallbackQueryHandler(handle_boost_selection, pattern=r'^boost$|boostpkg\|'),
        CallbackQueryHandler(handle_network_eth_callback, pattern=r'^network_eth$'),
        CallbackQueryHandler(handle_network_sol_callback, pattern=r'^network_sol$'),
        CallbackQueryHandler(handle_network_bnb_callback, pattern=r'^network_bnb$'),
        CallbackQueryHandler(handle_network_base_callback, pattern=r'^network_base$'),
        CallbackQueryHandler(handle_boost_token_callback, pattern=r'^boost$'), # Added handler for initial boost button
        CallbackQueryHandler(show_how_boost_works, pattern=r'^how_boost_works$')
    ]