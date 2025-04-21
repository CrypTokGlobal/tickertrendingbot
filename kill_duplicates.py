
#!/usr/bin/env python3
import os
import subprocess
import sys
import time

def kill_telegram_bot_instances():
    """Kill all running Telegram bot instances"""
    print("🔍 Finding and killing duplicate Telegram bot instances...")
    
    # Record current PID to avoid killing this script
    current_pid = os.getpid()
    killed_count = 0
    
    try:
        # Get all running Python processes
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        
        # Find PIDs of bot-related processes
        for line in lines:
            if "python" in line and ("main.py" in line or "start_bot.py" in line):
                # Extract PID (second column in ps aux output)
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        # Skip current process
                        if pid != current_pid:
                            print(f"Killing process {pid}: {line.strip()}")
                            os.kill(pid, 9)  # SIGKILL
                            killed_count += 1
                    except (ValueError, ProcessLookupError) as e:
                        print(f"Error with process: {e}")
        
        # Also remove any lock files
        for lockfile in ["bot.lock", "app.lock", "bot.pid"]:
            if os.path.exists(lockfile):
                os.remove(lockfile)
                print(f"Removed {lockfile} file")
                
        print(f"✅ Successfully killed {killed_count} duplicate processes")
        
    except Exception as e:
        print(f"❌ Error killing duplicates: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = kill_telegram_bot_instances()
    # Sleep briefly to allow OS to clean up processes
    time.sleep(1)
    sys.exit(exit_code)
