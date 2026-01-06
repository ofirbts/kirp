#!/usr/bin/env python3
"""
KIRP Status Reporter - הפעל וקבל דו"ח מלא
שלח לי את הפלט המלא בכל בעיה!
"""
import os
import sys
import subprocess
import requests
import json
from datetime import datetime
import pathlib

def run_cmd(cmd):
    """רץ פקודה ושמחזיר תוצאה"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else f"ERROR: {result.stderr.strip()}"
    except:
        return "TIMEOUT/ERROR"

def check_endpoint(url, method="GET", data=None):
    """בדוק endpoint"""
    try:
        if method == "POST":
            r = requests.post(url, json=data, timeout=5)
        else:
            r = requests.get(url, timeout=5)
        return f"{r.status_code}: {r.text[:200]}{'...' if len(r.text) > 200 else ''}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    print("=" * 60)
    print(f"KIRP STATUS REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. סביבה
    print("\n🖥️  ENVIRONMENT:")
    print(f"  Dir: {pathlib.Path.cwd()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Uvicorn: {'running' if os.system('pgrep -f uvicorn > /dev/null') == 0 else 'stopped'}")
    
    # 2. Backend
    print("\n🔌 BACKEND ENDPOINTS:")
    endpoints = {
        "Health": "http://127.0.0.1:8000/health/",
        "Tasks": "http://127.0.0.1:8000/tasks/",
        "Agent": ("http://127.0.0.1:8000/agent/", "POST", {"question": "status"}),
        "Weekly": ("http://127.0.0.1:8000/intelligence/weekly-summary", "POST", {}),
        "Query": ("http://127.0.0.1:8000/query/", "POST", {"question": "test"})
    }
    
    for name, spec in endpoints.items():
        if isinstance(spec, tuple):
            url, method, data = spec
        else:
            url, method, data = spec, "GET", None
        print(f"  {name:10}: {check_endpoint(url, method, data)}")
    
    # 3. קבצים
    print("\n📁 KEY FILES:")
    key_files = ["../" + f for f in key_files] 
    for f in key_files:
        if os.path.exists(f):
            print(f"  ✓ {f} ({os.path.getsize(f)} bytes)")
        else:
            print(f"  ✗ {f} MISSING")
    
    # 4. תהליכים
    print("\n⚙️  PROCESSES:")
    print(run_cmd("ps aux | grep uvicorn | grep -v grep"))
    print(run_cmd("ps aux | grep mongo | grep -v grep"))
    
    # 5. לוגים אחרונים
    print("\n📜 LAST LOGS:")
    print(run_cmd("tail -n 5 nohup.out 2>/dev/null || tail -n 5 app.log 2>/dev/null || echo 'No logs'"))
    
    print("\n" + "="*60)
    print("💡 העתק הכל ושלח לי - אפתור כל בעיה!")

if __name__ == "__main__":
    main()
