import os
import signal
import subprocess

ports = [8000, 8501, 8502, 8503]

for port in ports:
    print(f"Checking port {port}...")
    # פקודה שמוצאת את ה-PID שרץ על הפורט
    cmd = f"lsof -t -i:{port}"
    try:
        pid = subprocess.check_output(cmd, shell=True).decode().strip()
        if pid:
            pids = pid.split('\n')
            for p in pids:
                print(f"🔥 Killing process {p} on port {port}")
                os.kill(int(p), signal.SIGKILL)
    except subprocess.CalledProcessError:
        print(f"✅ Port {port} is already free")

print("\nAll targeted ports should be clean now.")
