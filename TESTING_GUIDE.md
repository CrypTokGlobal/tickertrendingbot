
# Testing Guide

This guide helps you verify that your Crypto Alert Bot is working correctly by testing different components.

## Basic Bot Functionality

### 1. Bot Initialization

1. Start the bot using the "Start Bot with Dashboard" workflow
2. Send `/start` to the bot on Telegram
3. You should receive a welcome message

### 2. Owner/Admin Setup

1. The first user to send `/start` becomes the owner
2. Test the admin commands:
   - `/allow <username or user_id>` to add an admin
   - `/admins` to list all admins
   - `/deny <username or user_id>` to remove an admin

## Token Tracking Tests

### 1. Ethereum Token Tracking

1. Track a test token:
   ```
   /track 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 Uniswap UNI 5
   ```
   
2. Verify tracking success with `/mytokens`

3. Test alerts:
   ```
   /test_eth
   ```
   
4. You should receive a test alert for the UNI token

### 2. Solana Token Tracking

1. Track a test Solana token:
   ```
   /tracksol EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v USDC USDC 5
   ```
   
2. Verify tracking success with `/mytokens`

3. Run `/example_alert` to test Solana alerts

### 3. BSC Token Tracking

1. Track a test BSC token:
   ```
   /trackbnb 0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82 PancakeSwap CAKE 5
   ```
   
2. Verify tracking success with `/mytokens`

### 4. Untracking Tokens

1. Untrack a token with:
   ```
   /untrack 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984
   ```
   
2. Verify the token was removed with `/mytokens`

## Customization Tests

### 1. Alert Customization

1. Start customization for a token:
   ```
   /customize 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984
   ```
   
2. Follow the prompts to add:
   - Token name, symbol
   - Social media links
   - Custom emojis
   - Image or GIF

3. Test the customized alert with:
   ```
   /preview 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984
   ```

## Bot Status and Dashboard

### 1. Status Command

1. Check bot status with `/status`
2. Verify it shows:
   - Bot uptime
   - Tracked tokens
   - Web3 connection status

### 2. Web Dashboard

1. Access the dashboard at:
   ```
   https://[your-replit-username].[repl-name].repl.co/status
   ```
   
2. Verify the dashboard shows:
   - Bot status
   - Tracked tokens list
   - Recent alerts (if any)

## Debug Commands (Owner Only)

1. Test data integrity with:
   ```
   /debug_data
   ```
   
2. View tracked tokens by chat:
   ```
   /debug_tokens
   ```
   
3. View group data:
   ```
   /debug_groups
   ```
   
4. View specific token data:
   ```
   /debug_token UNI
   ```

## Alert System Stress Test

1. Track several tokens (3-5) across different blockchains
2. Run `/test_alert` to generate alerts for all tokens
3. Verify all alerts are received correctly
4. Check alert formatting, buttons, and links are working

## Common Issues and Solutions

### No Alerts Received

- Check if the token address is correct
- Verify the minimum USD value isn't set too high
- Ensure the bot has permission to send messages in the chat
- Check Replit logs for connection errors

### Connection Issues

- Verify API keys and endpoints are correct
- Check Replit logs for timeout or connection errors
- Restart the bot with `/restart` (admin only)

### Database Issues

- Use `/debug_data` to check data integrity
- If necessary, reset tracking and start fresh
