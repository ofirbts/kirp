#!/usr/bin/env python3
"""
KIRP OS v7 - Production Status Reporter
Comprehensive system diagnostic + health check
"""
import os
import sys
import subprocess
import requests
import json
from datetime import datetime, timezone
from pathlib import Path

class KIRPStatus:
    """Production diagnostic tool"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = {}
    
    def run_command(self, cmd: str) -> str:
        """Execute shell command safely"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=15
            )
            return result.stdout.strip() if result.returncode == 0 else f"❌ {result.stderr.strip()}"
        except:
            return "❌ TIMEOUT/ERROR"
    
    def check_endpoint(self, endpoint: str, method: str = "GET", data: dict = None) -> str:
        """Test API endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            if method == "POST":
                resp = requests.post(url, json=data, timeout=10)
            else:
                resp = requests.get(url, timeout=10)
            return f"🟢 {resp.status_code}"
        except Exception as e:
            return f"🔴 ERROR: {str(e)[:50]}"
    
    def diagnostic_report(self):
        """Full production diagnostic"""
        print("\n" + "="*80)
        print(f"🚀 KIRP OS v7 STATUS REPORT - {datetime.now(timezone.utc)}")
        print("="*80)
        
        # 1. Environment
        print("\n🖥️  ENVIRONMENT:")
        print(f"   Python: {sys.version.split()[0]}")
        print(f"   Dir: {Path.cwd()}")
        print(f"   Docker: {'🟢' if Path('docker-compose.yml').exists() else '🔴'}")
        
        # 2. Services
        print("\n🔌 SERVICES:")
        print(f"   API Health: {self.check_endpoint('/health')}")
        print(f"   API Status: {self.check_endpoint('/status')}")
        print(f"   UI Live: {self.check_endpoint('/health', 'http://localhost:8501')}")
        
        # 3. Processes
        print("\n⚙️  PROCESSES:")
        print("   API:", self.run_command("docker ps | grep kirp-api"))
        print("   Worker:", self.run_command("docker ps | grep kirp-worker"))
        
        # 4. Logs
        print("\n📜 RECENT LOGS:")
        print(self.run_command("docker logs kirp-api --tail 5 2>/dev/null || echo 'No logs'"))
        
        # 5. Summary
        print("\n" + "="*80)
        healthy = all([
            "🟢" in self.check_endpoint('/health'),
            Path('docker-compose.yml').exists()
        ])
        print(f"🏁 STATUS: {'🟢 PRODUCTION READY' if healthy else '🔴 NEEDS ATTENTION'}")
        print("="*80)

if __name__ == "__main__":
    KIRPStatus().diagnostic_report()
