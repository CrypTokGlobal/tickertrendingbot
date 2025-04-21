
#!/usr/bin/env python3
import os
import signal
import subprocess
import sys

print("✅ Running kill_bots.py to ensure clean start")

# Get all Python processes
try:
    output = subprocess.check_output(["ps", "aux"]).decode()
    lines = output.strip().split('\n')
    
    # Find PIDs of Python processes running main.py or start_bot.py
    for line in lines:
        if "python" in line and ("main.py" in line or "start_bot.py" in line):
            # Extract PID (second column in ps aux output)
            parts = line.split()
            if len(parts) >= 2:
                try:
                    pid = int(parts[1])
                    print(f"Killing process {pid}: {line.strip()}")
                    os.kill(pid, signal.SIGKILL)
                except (ValueError, ProcessLookupError) as e:
                    print(f"Error killing process: {e}")
    
    # Also remove any lock files
    if os.path.exists("app.lock"):
        os.remove("app.lock")
        print("Removed app.lock file")
        
    print("✅ All bot processes cleaned up")
    
except Exception as e:
    print(f"Error in kill_bots.py: {e}")
    sys.exit(1)
