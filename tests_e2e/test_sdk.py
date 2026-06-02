import json
from pathlib import Path
import pytest

BASE = Path(__file__).resolve().parent.parent / "brand_os_v3"

def test_load_identity():
    from brand_os_sdk import load_identity
    assert isinstance(load_identity(), dict)

def test_load_voice():
    from brand_os_sdk import load_voice
    assert isinstance(load_voice(), dict)

def test_list_agents():
    from brand_os_sdk import list_agents
    a = list_agents()
    assert isinstance(a, list) and "CONTEXT_SCANNER" in a

def test_run_orchestrator():
    from brand_os_sdk import run_orchestrator
    r = run_orchestrator({"tenant_id": "e2e", "platform": "linkedin", "topic_hint": "test"})
    assert isinstance(r, dict) and "content" in r and "status" in r
    assert r["status"] in ("approved", "rejected_identity", "rejected_cto")
