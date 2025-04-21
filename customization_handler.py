import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Global dictionary to hold token customizations
token_customizations = {}

def load_customizations():
    """Load token customizations from file"""
    global token_customizations

    try:
        if os.path.exists("customizations.json"):
            with open("customizations.json", "r") as f:
                token_customizations = json.load(f)
                logger.info(f"Loaded {len(token_customizations)} token customizations")
        else:
            logger.info("No customizations file found, starting with empty customizations")
            token_customizations = {}
        return token_customizations
    except Exception as e:
        logger.error(f"Error loading customizations: {e}")
        token_customizations = {}
        return {}

def save_customizations():
    """Save token customizations to file"""
    try:
        with open("customizations.json", "w") as f:
            json.dump(token_customizations, f, indent=2)
        logger.info(f"Saved {len(token_customizations)} token customizations")
        return True
    except Exception as e:
        logger.error(f"Error saving customizations: {e}")
        return False

def add_customization(token_address, data):
    """Add or update token customization"""
    global token_customizations

    # Normalize address
    token_address = token_address.lower() if token_address.startswith("0x") else token_address

    # Update customization
    token_customizations[token_address] = data

    # Save to file
    save_customizations()

    return True

def apply_token_customization(token_address: str, alert_message: str) -> tuple:
    """Apply token customization to an alert message and return media info if available"""
    token_address = token_address.lower() if token_address.startswith("0x") else token_address
    custom = get_customization(token_address)
    
    if not custom:
        return alert_message, None
    
    # Extract media information if available
    media = None
    if "media" in custom and custom["media"]:
        media = custom["media"]
    
    # Return the alert message and media info
    return alert_message, media

def remove_customization(token_address):
    """Remove token customization"""
    global token_customizations

    # Normalize address
    token_address = token_address.lower() if token_address.startswith("0x") else token_address

    # Check if customization exists
    if token_address not in token_customizations:
        return False

    # Remove customization
    del token_customizations[token_address]

    # Save to file
    save_customizations()

    return True

def get_customization(token_address):
    """Get token customization"""
    # Normalize address
    token_address = token_address.lower() if token_address.startswith("0x") else token_address

    return token_customizations.get(token_address, {})

import json
import logging
import os
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global dictionary to store token customizations
token_customizations = {}  # {token_address: {logo: url, links: {...}, emojis: "..."}}

def save_customizations():
    """Save token customizations to a JSON file"""
    try:
        with open("token_customizations.json", "w") as f:
            json.dump(token_customizations, f, indent=2)
        logger.info(f"✅ Saved {len(token_customizations)} token customizations to file")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving customizations: {e}")
        return False

def load_customizations():
    """Load token customizations from a JSON file"""
    global token_customizations

    if not os.path.exists("token_customizations.json"):
        logger.info("No customizations file found, starting with empty customizations")
        return {}

    try:
        with open("token_customizations.json", "r") as f:
            token_customizations = json.load(f)
        logger.info(f"✅ Loaded {len(token_customizations)} token customizations from file")
        return token_customizations
    except Exception as e:
        logger.error(f"❌ Error loading customizations: {e}")
        return {}

def add_customization(token_address: str, customization_data: Dict[str, Any]) -> bool:
    """Add or update customization for a token"""
    global token_customizations

    token_address = token_address.lower()  # Normalize to lowercase

    # Store customization data
    token_customizations[token_address] = customization_data

    # Save to file
    success = save_customizations()
    return success

def get_customization(token_address: str) -> Optional[Dict[str, Any]]:
    """Get customization data for a token"""
    token_address = token_address.lower()  # Normalize to lowercase
    return token_customizations.get(token_address)

def remove_customization(token_address: str) -> bool:
    """Remove customization for a token"""
    global token_customizations

    token_address = token_address.lower()  # Normalize to lowercase

    if token_address in token_customizations:
        del token_customizations[token_address]
        success = save_customizations()
        return success
    return False

def apply_token_customization(token_address: str, alert_message: str) -> str:
    """Apply token customization to an alert message"""
    # Simple version without media handling
    return alert_message

# Load customizations when module is imported
load_customizations()

def get_token_customization_handler():
    """Get the token customization conversation handler"""
    from telegram.ext import (
        ConversationHandler, CommandHandler, 
        MessageHandler, filters, CallbackQueryHandler
    )
    from token_customizer import (
        start_customization, handle_contract, handle_name, 
        handle_symbol, handle_telegram, handle_website, 
        handle_twitter, handle_image, handle_emojis, 
        handle_media, handle_confirm, cancel
    )
    from token_customizer import CONTRACT, NAME, SYMBOL, TELEGRAM, WEBSITE, TWITTER, IMAGE, EMOJIS, MEDIA, CONFIRM
    
    return ConversationHandler(
        entry_points=[CommandHandler("customize_token", start_customization)],
        states={
            CONTRACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contract)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symbol)],
            TELEGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram)],
            WEBSITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_website)],
            TWITTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_twitter)],
            IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_image)],
            EMOJIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_emojis)],
            MEDIA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_media),
                MessageHandler(filters.PHOTO | filters.Document.ALL | filters.ANIMATION | filters.Sticker.ALL, handle_media)
            ],
            CONFIRM: [CallbackQueryHandler(handle_confirm, pattern="^(confirm|cancel)_customization$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="token_customization",
    )

def get_customization_handlers():
    """Get additional customization-related handlers"""
    return []

async def list_customizations(update, context):
    """List all token customizations for the user"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Get all customizations
    customizations = token_customizations
    
    if not customizations:
        await update.message.reply_text("No token customizations found.")
        return
    
    # Format the list of customizations
    message = "🎨 *Token Customizations*\n\n"
    
    for token_address, custom in customizations.items():
        name = custom.get("name", "Unknown")
        symbol = custom.get("symbol", "???")
        emojis = custom.get("emojis", "🚀")
        
        # Display token with shortened address
        short_address = f"{token_address[:8]}...{token_address[-6:]}" if len(token_address) > 14 else token_address
        
        message += f"*{name}* ({symbol}) {emojis}\n"
        message += f"└ `{short_address}`\n\n"
    
    message += "Use `/preview <token_address>` to see how alerts will look.\n"
    message += "Use `/reset_custom <token_address>` to remove customization."
    
    await update.message.reply_text(message, parse_mode="MARKDOWN")

async def preview_customization(update, context):
    """Preview a token alert with customization applied"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please provide a token address. Example: `/preview 0x123...`", 
            parse_mode="MARKDOWN"
        )
        return
    
    token_address = context.args[0]
    
    # Normalize address
    token_address = token_address.lower() if token_address.startswith("0x") else token_address
    
    # Get the customization
    custom = get_customization(token_address)
    
    if not custom:
        await update.message.reply_text(
            f"⚠️ No customization found for token: `{token_address}`\n"
            f"Use `/customize_token {token_address}` to create one.",
            parse_mode="MARKDOWN"
        )
        return
    
    # Extract customization info
    name = custom.get("name", "Token Name")
    symbol = custom.get("symbol", "TKN")
    telegram = custom.get("links", {}).get("telegram", "")
    website = custom.get("links", {}).get("website", "")
    twitter = custom.get("links", {}).get("twitter", "")
    emoji_set = custom.get("emojis", "🚀")
    image_url = custom.get("image", "")
    
    # Create buttons for preview
    buttons = []
    
    if telegram:
        buttons.append([InlineKeyboardButton("💬 Telegram", url=telegram)])
    
    if website:
        buttons.append([InlineKeyboardButton("🌐 Website", url=website)])
    
    if twitter:
        buttons.append([InlineKeyboardButton("🐦 Twitter/X", url=twitter)])
    
    # Add chart and buy buttons for completeness
    chain = "ethereum" if token_address.startswith("0x") else "solana"
    chart_url = f"https://dexscreener.com/{chain}/{token_address}"
    buy_url = f"https://app.uniswap.org/#/swap?outputCurrency={token_address}" if chain == "ethereum" else f"https://raydium.io/swap/?inputCurrency=SOL&outputCurrency={token_address}"
    
    buttons.append([InlineKeyboardButton("📊 Chart", url=chart_url)])
    buttons.append([InlineKeyboardButton("💰 Buy Now", url=buy_url)])
    
    # Create preview message
    preview = (
        f"{emoji_set} *{name}* ({symbol}) {emoji_set}\n\n"
        f"🟢 Someone just bought for $1,000 (1.5 SOL)\n\n"
        f"📈 24h Change: +15%\n"
        f"💰 24h Volume: $250,000\n"
        f"💎 Market Cap: $5,000,000\n\n"
        f"🧑‍🚀 Holders: 1,200\n"
        f"⏱ Created: 7 days ago\n\n"
        f"*This is a preview of how your customized alert will look!*"
    )
    
    if image_url:
        await update.message.reply_photo(
            photo=image_url,
            caption=preview,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="MARKDOWN"
        )
    else:
        await update.message.reply_text(
            preview,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="MARKDOWN"
        )

async def reset_customization(update, context):
    """Reset (remove) a token customization"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please provide a token address. Example: `/reset_custom 0x123...`", 
            parse_mode="MARKDOWN"
        )
        return
    
    token_address = context.args[0]
    
    # Normalize address
    token_address = token_address.lower() if token_address.startswith("0x") else token_address
    
    # Get the customization
    custom = get_customization(token_address)
    
    if not custom:
        await update.message.reply_text(
            f"⚠️ No customization found for token: `{token_address}`",
            parse_mode="MARKDOWN"
        )
        return
    
    # Remove the customization
    result = remove_customization(token_address)
    
    if result:
        await update.message.reply_text(
            f"✅ Customization for token `{token_address}` has been removed.",
            parse_mode="MARKDOWN"
        )
    else:
        await update.message.reply_text(
            f"❌ Failed to remove customization for token `{token_address}`.",
            parse_mode="MARKDOWN"
        )