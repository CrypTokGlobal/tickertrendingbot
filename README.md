
# Crypto Alert Bot

A powerful Telegram bot for tracking cryptocurrency tokens across multiple blockchains (Ethereum, Solana, Binance Smart Chain) and sending real-time alerts about significant transactions.

## Features

- Track tokens across Ethereum, Solana, and BSC networks
- Get real-time alerts for significant buy/sell transactions
- Customizable alerts with images, GIFs, or stickers
- Boost feature for promoting tokens to partner channels
- Admin command system for bot management
- Web dashboard for monitoring bot status
- Multi-group support for tracking different tokens in different chats

## Setup Guide

### Environment Variables

Set up the following variables in your Replit Secrets:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `INFURA_URL`: Ethereum API endpoint (from Infura or another provider)
- `SOLANA_RPC_URL`: Solana RPC endpoint (optional)
- `BSC_NODE_URL`: Binance Smart Chain RPC endpoint (optional)
- `ADMIN_CHAT_ID`: Telegram chat ID for admin notifications (optional)
- `ETHERSCAN_API_KEY`: Etherscan API key (optional)
- `BSCSCAN_API_KEY`: BSC Scan API key (optional)

### Installation

1. Clone this repository
2. Set the environment variables mentioned above
3. Run the Start Bot workflow (or `python start_bot.py`)
4. Access your bot on Telegram

### Running the Bot

The bot can be started using the "Start Bot with Dashboard" workflow.

## Commands

### Basic Commands

- `/start` - Initialize the bot
- `/help` - Show available commands
- `/status` - Check bot status and tracked tokens

### Token Tracking

- `/track 0xADDRESS TokenName SYMBOL 5` - Track Ethereum token
- `/tracksol SOLANADDRESS TokenName SYMBOL 5` - Track Solana token
- `/trackbnb 0xADDRESS TokenName SYMBOL 5` - Track BSC token
- `/untrack ADDRESS` - Stop tracking a token
- `/mytokens` - List all tokens being tracked in current chat

### Testing

- `/test_alert` - Generate test alerts for tracked tokens
- `/test_eth` - Test Ethereum alert specifically

### Customization

- `/customize ADDRESS` - Add custom logo, links, and emojis to alerts

### Admin Commands

- `/allow USERNAME_OR_ID` - Grant admin access to user (owner only)
- `/deny USERNAME_OR_ID` - Remove admin access (owner only)
- `/admins` - List all admin users
- `/restart` - Restart the bot (admin only)

## Dashboard

A web dashboard is available at:
`https://[your-replit-username].[repl-name].repl.co/status`

## License

This project is licensed for personal and educational use only.
