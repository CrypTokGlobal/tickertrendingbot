
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from auth_decorators import owner_only
from transaction_utils import load_transaction_data
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@owner_only
async def debug_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to view the full transaction data"""
    try:
        # Load current data
        data = load_transaction_data()
        
        # Add timestamp for reference
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a summary message
        msg = f"🔍 *Transaction Data Debug* ({current_time})\n\n"
        
        # Add token counts
        tokens = data.get("tracked_tokens", [])
        eth_tokens = [t for t in tokens if t.get("network", "").lower() == "ethereum"]
        sol_tokens = [t for t in tokens if t.get("network", "").lower() == "solana"]
        msg += f"📊 *Token Summary:*\n"
        msg += f"• Total tracked tokens: {len(tokens)}\n"
        msg += f"• Ethereum tokens: {len(eth_tokens)}\n"
        msg += f"• Solana tokens: {len(sol_tokens)}\n\n"
        
        # Add group counts
        groups = data.get("groups", {})
        msg += f"👥 *Group Summary:*\n"
        msg += f"• Total groups: {len(groups)}\n"
        
        # Active groups count
        active_groups = sum(1 for g in groups.values() if g.get("active", False))
        msg += f"• Active groups: {active_groups}\n\n"
        
        # Add settings info if present
        chat_settings = data.get("chat_settings", {})
        msg += f"⚙️ *Chat Settings:*\n"
        msg += f"• Configured chats: {len(chat_settings)}\n\n"
        
        # Add database status or last updated if available
        if "last_updated" in data:
            msg += f"🕒 *Last Updated:* {data['last_updated']}\n\n"
        
        # Create refresh button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="debug_data_refresh")],
            [InlineKeyboardButton("📊 View Tokens", callback_data="debug_tokens_view")],
            [InlineKeyboardButton("👥 View Groups", callback_data="debug_groups_view")]
        ])
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in debug_data: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error accessing transaction data: {str(e)}")

@owner_only
async def debug_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to view tracked tokens by chat"""
    try:
        # Load current data
        data = load_transaction_data()
        tokens = data.get("tracked_tokens", [])
        
        if not tokens:
            await update.message.reply_text("No tokens are currently being tracked.")
            return
        
        # Group tokens by chat_id
        tokens_by_chat = {}
        for token in tokens:
            chat_id = token.get("chat_id")
            if chat_id:
                if chat_id not in tokens_by_chat:
                    tokens_by_chat[chat_id] = []
                tokens_by_chat[chat_id].append(token)
        
        # Find ungrouped tokens (no chat_id)
        ungrouped_tokens = [t for t in tokens if "chat_id" not in t]
        
        # Create a formatted message
        msg = f"🔍 *Tracked Tokens by Chat* (Total: {len(tokens)})\n\n"
        
        # Add tokens by chat
        for chat_id, chat_tokens in tokens_by_chat.items():
            eth_tokens = [t for t in chat_tokens if t.get("network", "").lower() == "ethereum"]
            sol_tokens = [t for t in chat_tokens if t.get("network", "").lower() == "solana"]
            
            msg += f"👥 *Chat ID:* `{chat_id}`\n"
            msg += f"• Total tokens: {len(chat_tokens)}\n"
            
            if eth_tokens:
                msg += f"• *Ethereum Tokens:*\n"
                for token in eth_tokens:
                    symbol = token.get("symbol", "???")
                    address = token.get("address", "Unknown")
                    min_usd = token.get("min_volume_usd", 0)
                    short_addr = f"{address[:8]}...{address[-6:]}" if len(address) > 14 else address
                    msg += f"  - {symbol} (`{short_addr}`) min: ${min_usd}\n"
            
            if sol_tokens:
                msg += f"• *Solana Tokens:*\n"
                for token in sol_tokens:
                    symbol = token.get("symbol", "???")
                    address = token.get("address", "Unknown")
                    min_usd = token.get("min_volume_usd", 0)
                    short_addr = f"{address[:8]}...{address[-6:]}" if len(address) > 14 else address
                    msg += f"  - {symbol} (`{short_addr}`) min: ${min_usd}\n"
            
            msg += "\n"
        
        # Add ungrouped tokens section if any exist
        if ungrouped_tokens:
            msg += f"🛠 *Ungrouped Tokens* (no chat_id assigned)\n"
            for token in ungrouped_tokens:
                symbol = token.get("symbol", "???")
                address = token.get("address", "Unknown")
                network = token.get("network", "unknown")
                short_addr = f"{address[:8]}...{address[-6:]}" if len(address) > 14 else address
                msg += f"- {symbol} (`{short_addr}`) on {network}\n"
        
        # If message is too long, split it
        if len(msg) > 4000:
            chunks = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await update.message.reply_text(chunk, parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"... (continued {i+1}/{len(chunks)})\n\n{chunk}", parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in debug_tokens: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error accessing token data: {str(e)}")

@owner_only
async def debug_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to view group data"""
    try:
        # Load current data
        data = load_transaction_data()
        groups = data.get("groups", {})
        
        if not groups:
            await update.message.reply_text("No groups are currently registered.")
            return
        
        # Create a formatted message
        msg = f"🔍 *Registered Groups* (Total: {len(groups)})\n\n"
        
        # Count active groups
        active_groups = sum(1 for g in groups.values() if g.get("active", True))
        msg += f"✅ Active groups: {active_groups}\n"
        msg += f"❌ Inactive groups: {len(groups) - active_groups}\n\n"
        
        # Add groups data
        for chat_id, group_data in groups.items():
            name = group_data.get("name", "Unknown Group")
            is_active = group_data.get("active", False)
            is_admin = group_data.get("is_admin", False)
            registered_at = group_data.get("registered_at", "Unknown")
            last_activity = group_data.get("last_activity", "Never")
            
            status = "✅ Active" if is_active else "❌ Inactive"
            admin_status = "👑 Admin" if is_admin else "👤 Member"
            
            msg += f"*Group:* {name}\n"
            msg += f"• Chat ID: `{chat_id}`\n"
            msg += f"• Status: {status}, {admin_status}\n"
            msg += f"• Registered: {registered_at}\n"
            msg += f"• Last Activity: {last_activity}\n\n"
        
        # If message is too long, split it
        if len(msg) > 4000:
            chunks = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await update.message.reply_text(chunk, parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"... (continued {i+1}/{len(chunks)})\n\n{chunk}", parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in debug_groups: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error accessing group data: {str(e)}")

@owner_only
async def debug_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to view a specific token's full data"""
    if not context.args:
        await update.message.reply_text("Usage: /debug_token SYMBOL_OR_ADDRESS")
        return
    
    try:
        search_term = context.args[0].upper()
        data = load_transaction_data()
        tokens = data.get("tracked_tokens", [])
        
        # Search by symbol or address
        matches = [t for t in tokens if 
                  t.get("symbol", "").upper() == search_term or 
                  t.get("address", "").lower() == search_term.lower()]
        
        if not matches:
            await update.message.reply_text(f"No token found with symbol or address: {search_term}")
            return
        
        # Display each matching token
        for i, token in enumerate(matches):
            symbol = token.get("symbol", "???")
            address = token.get("address", "Unknown")
            network = token.get("network", "unknown")
            chat_id = token.get("chat_id", "None")
            
            # Format as pretty JSON for readability
            token_json = json.dumps(token, indent=2)
            
            await update.message.reply_text(
                f"🔍 *Token Details ({i+1}/{len(matches)})*\n\n"
                f"• Symbol: {symbol}\n"
                f"• Network: {network}\n"
                f"• Chat ID: {chat_id}\n"
                f"• Address: `{address}`\n\n"
                f"```\n{token_json}\n```",
                parse_mode="Markdown"
            )
        
    except Exception as e:
        logger.error(f"Error in debug_token: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_debug_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks for debug commands"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "debug_data_refresh":
        # Update the message with refreshed data
        await debug_data(update, context)
    elif query.data == "debug_tokens_view":
        # Show tokens view
        await query.edit_message_text("Loading tokens data...")
        await debug_tokens(update, context)
    elif query.data == "debug_groups_view":
        # Show groups view
        await query.edit_message_text("Loading groups data...")
        await debug_groups(update, context)

def get_data_debug_handlers():
    """Return list of handlers for debugging data"""
    return [
        CommandHandler("debug_data", debug_data),
        CommandHandler("debug_tokens", debug_tokens),
        CommandHandler("debug_groups", debug_groups),
        CommandHandler("debug_token", debug_token),
        CallbackQueryHandler(handle_debug_callback, pattern="^debug_")
    ]
