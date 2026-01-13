#!/usr/bin/env python3
"""
KIRP SYSTEM DIAGNOSTIC HARNESS
Layered, severity-aware, demo-grade system check
"""

import os
import requests
import sys
from dataclasses import dataclass
from typing import Optional

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")
HEADERS = {"X-Tenant": "default"}

# -------------------- Result Model --------------------

@dataclass
class CheckResult:
    name: str
    ok: bool
    severity: str  # OK / WARN / FAIL
    detail: Optional[str] = None

results = []

def record(name, ok=True, severity="OK", detail=None):
    results.append(CheckResult(name, ok, severity, detail))
    icon = "✅" if severity == "OK" else "⚠️" if severity == "WARN" else "❌"
    print(f"{icon} {name}")
    if detail:
        print(f"    ↳ {detail}")

# -------------------- Helpers --------------------

def http_ok(r):
    # Accept 200–308 as valid for infra
    return 200 <= r.status_code < 309

def safe_get(path):
    return requests.get(BASE + path, headers=HEADERS)

def safe_post(path, payload):
    return requests.post(BASE + path, json=payload, headers=HEADERS)

# -------------------- Layer 0: Infra --------------------

print("\n=== INFRA ===")

try:
    r = safe_get("/health/")
    if http_ok(r):
        record("API /health", True)
    else:
        record("API /health", False, "FAIL", f"status={r.status_code}")
except Exception as e:
    record("API /health", False, "FAIL", str(e))
    sys.exit(1)

# -------------------- Layer 1: Status --------------------

print("\n=== CORE STATUS ===")

r = safe_get("/status/")
if http_ok(r):
    record("/status", True)
else:
    record("/status", False, "FAIL")

# -------------------- Layer 2: Debug / State --------------------

print("\n=== STATE & EVENTS ===")

r = safe_get("/debug/agent/state")
if http_ok(r):
    record("Agent state accessible", True)
else:
    record("Agent state accessible", False, "WARN")

r = safe_get("/debug/events")
if http_ok(r):
    record("Event log accessible", True)
else:
    record("Event log accessible", False, "WARN")

# -------------------- Layer 3: RAG --------------------

print("\n=== RAG PIPELINE ===")

payload = {"question": "What is KIRP?", "k": 3, "session_id": "diag"}

r = safe_post("/query", payload)
if http_ok(r):
    record("RAG /query", True)
else:
    record("RAG /query", False, "FAIL", r.text)

# -------------------- Layer 4: Agent --------------------

print("\n=== AGENT ===")

r = safe_post("/agent/query/", payload)
if http_ok(r):
    record("Agent /agent/query", True)
else:
    record("Agent /agent/query", False, "FAIL", r.text)

# -------------------- Layer 5: Stream --------------------

print("\n=== STREAMING ===")

try:
    r = requests.post(BASE + "/query/stream", json=payload, stream=True)
    if r.status_code == 200:
        record("Query streaming", True)
    else:
        record("Query streaming", False, "WARN", f"status={r.status_code}")
except Exception as e:
    record("Query streaming", False, "WARN", str(e))

# -------------------- Layer 6: Observability --------------------

print("\n=== OBSERVABILITY ===")

r = safe_get("/observability/metrics")
if http_ok(r):
    record("Observability metrics", True)
else:
    record("Observability metrics", False, "WARN")

# -------------------- Layer 7: Policy / Governance --------------------

print("\n=== GOVERNANCE ===")

r = safe_get("/policy/")
if http_ok(r):
    record("Policy engine present", True)
else:
    record("Policy engine present", False, "WARN")

# -------------------- Layer 8: Integrations --------------------

print("\n=== INTEGRATIONS ===")

r = safe_get("/webhooks/whatsapp/")
if http_ok(r):
    record("WhatsApp webhook reachable", True)
else:
    record("WhatsApp webhook reachable", False, "WARN")

# -------------------- SUMMARY --------------------

print("\n=== SUMMARY ===")

failures = [r for r in results if r.severity == "FAIL"]
warnings = [r for r in results if r.severity == "WARN"]

print(f"✅ OK: {len(results) - len(failures) - len(warnings)}")
print(f"⚠️ WARN: {len(warnings)}")
print(f"❌ FAIL: {len(failures)}")

if failures:
    print("\nSystem is NOT demo-ready.")
else:
    print("\n🎉 System is DEMO-READY (with warnings).")
