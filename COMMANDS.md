# Bot Commands Reference

## General Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize the bot and register user | `/start` |
| `/help` | Show help information and available commands | `/help` |
| `/status` | Display bot status and tracked tokens | `/status` |
| `/dashboard` | Get a link to the web dashboard | `/dashboard` |

## Token Tracking

| Command | Description | Example |
|---------|-------------|---------|
| `/track` | Track an Ethereum token | `/track 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 Uniswap UNI 10` |
| `/tracksol` | Track a Solana token | `/tracksol EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v USDC USDC 10` |
| `/trackbnb` | Track a Binance Smart Chain token | `/trackbnb 0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82 PancakeSwap CAKE 10` |
| `/untrack` | Stop tracking a token | `/untrack 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984` |
| `/mytokens` | List all tokens being tracked in current chat | `/mytokens` |

## Testing and Alerts

| Command | Description | Example |
|---------|-------------|---------|
| `/test_alert` | Generate test alerts for all tracked tokens | `/test_alert` |
| `/test_eth` | Test Ethereum alert specifically | `/test_eth` |
| `/register_chat` | Register current chat for alerts | `/register_chat` |
| `/example_alert` | Show example alert format | `/example_alert` |

## Customization

| Command | Description | Example |
|---------|-------------|---------|
| `/customize` | Customize token alerts with logo, links and emojis | `/customize 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984` |
| `/reset_custom` | Remove customization for a token | `/reset_custom 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984` |
| `/preview` | Preview how customized alerts will look | `/preview 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984` |

## Boost Features

| Command | Description | Example |
|---------|-------------|---------|
| `/boost` | Boost a token to partner channels | `/boost 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984` |

## Admin Commands (Owner/Admins only)

| Command | Description | Example |
|---------|-------------|---------|
| `/allow` | Grant admin access to user (owner only) | `/allow @username` or `/allow 123456789` |
| `/deny` | Remove admin access from user (owner only) | `/deny @username` or `/deny 123456789` |
| `/admins` | List all admin users | `/admins` |
| `/admin` | Open admin control panel | `/admin` |
| `/restart` | Restart the bot (admin only) | `/restart` |
| `/kill_dupes` | Kill duplicate bot processes (admin only) | `/kill_dupes` |
| `/broadcast` | Send a message to all active chats (admin only) | `/broadcast Important update: new features added!` |

## Debugging Commands (Owner only)

| Command | Description | Example |
|---------|-------------|---------|
| `/debug_data` | View the full transaction data | `/debug_data` |
| `/debug_tokens` | View tracked tokens by chat | `/debug_tokens` |
| `/debug_groups` | View group data | `/debug_groups` |
| `/debug_token` | View a specific token's full data | `/debug_token UNI` or `/debug_token 0x1f9840a85d...` |
| `/emergency_reset_admins` | Reset all admin access (owner only) | `/emergency_reset_admins` |