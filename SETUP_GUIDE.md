
# Crypto Alert Bot - Setup Guide

This document provides detailed instructions for setting up and configuring your Crypto Alert Bot.

## Initial Setup

### 1. Required Environment Variables

Set these in Replit Secrets (or .env file):

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from BotFather | Yes |
| `INFURA_URL` | Ethereum API endpoint URL | Yes |
| `SOLANA_RPC_URL` | Solana RPC endpoint URL | No (for Solana tracking) |
| `BSC_NODE_URL` | Binance Smart Chain RPC endpoint URL | No (for BSC tracking) |
| `ADMIN_CHAT_ID` | Chat ID for admin notifications | No |
| `ETHERSCAN_API_KEY` | API key for Etherscan | No |
| `BSCSCAN_API_KEY` | API key for BSCScan | No |

### 2. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to name your bot
4. Copy the API token provided and add it to your environment variables
5. Set bot commands with BotFather using `/setcommands`

### 3. Starting the Bot

1. Run the "Start Bot with Dashboard" workflow or execute:
```
python start_bot.py
```

2. The bot will start and initialize all necessary files if they don't exist
3. Visit your bot on Telegram and send `/start` to become the owner

## Configuration

### Setting Up Administrators

The first user to send `/start` will become the bot owner. The owner can:

1. Add admins with `/allow <username or user_id>`
2. Remove admins with `/deny <username or user_id>`
3. View all admins with `/admins`

### Tracking Tokens

To track tokens on different blockchains:

1. **Ethereum**: `/track 0xADDRESS TokenName SYMBOL 5`
   - ADDRESS: The token's contract address
   - TokenName: Human-readable name of the token
   - SYMBOL: Trading symbol for the token
   - 5: Minimum transaction value in USD to trigger alerts (optional)

2. **Solana**: `/tracksol SOLANADDRESS TokenName SYMBOL 5`

3. **Binance Smart Chain**: `/trackbnb 0xADDRESS TokenName SYMBOL 5`

### Customizing Alerts

Make your alerts more appealing with:

1. `/customize ADDRESS` - Starts a conversation to customize:
   - Token logo/image
   - Social media links (Telegram, Twitter, Website)
   - Custom emojis for alerts

## Testing

Ensure your setup is working correctly:

1. `/test_alert` - Generate example alerts for all tracked tokens
2. `/test_eth` - Test Ethereum alerts specifically
3. `/status` - Check the bot's status and list tracked tokens

## Dashboard Access

A web dashboard is available at:
`https://[your-replit-username].[repl-name].repl.co/status`

The dashboard shows:
- Bot uptime
- Tracked tokens by blockchain
- Recent alerts
- Active chat count

## Troubleshooting

### Common Issues

1. **Bot not responding**:
   - Check if the bot is running (`/status`)
   - Verify environment variables are set correctly
   - Check Replit logs for errors

2. **No alerts being received**:
   - Ensure minimum transaction value isn't set too high
   - Verify the token address is correct
   - Run `/test_alert` to verify notification delivery

3. **Database issues**:
   - Use `/debug_data` (owner only) to check data integrity

### Contact and Support

For issues or questions, create an issue on GitHub or contact the developer through Telegram.
