
#!/bin/bash
echo "👋 Bot is launching..."
echo "📊 Dashboard will be available at: https://${REPL_SLUG}.${REPL_OWNER}.repl.co/status"

# First kill any existing bot instances
python kill_duplicates.py

# Wait for processes to clean up
sleep 1

# Start the bot with dashboard support
python start_bot.py
