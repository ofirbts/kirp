from brand_os_sdk.kirp_integration import handle_kirp_event

def test_run_started():
    r = handle_kirp_event({"event_type": "brand_os_run_started", "payload": {"tenant_id": "t1", "platform": "linkedin", "topic_hint": "API"}})
    assert r is not None and "status" in r

def test_agent_completed():
    r = handle_kirp_event({"event_type": "agent_completed", "payload": {"trace_id": "tr1"}})
    assert r is not None and r.get("route") == "agent_completed"

def test_gatekeeper():
    r = handle_kirp_event({"event_type": "gatekeeper_decision", "payload": {"trace_id": "tr1"}})
    assert r is not None and r.get("route") == "gatekeeper_decision"

def test_run_completed():
    r = handle_kirp_event({"event_type": "run_completed", "payload": {"trace_id": "tr1"}})
    assert r is not None and r.get("route") == "run_completed"

def test_run_failed():
    r = handle_kirp_event({"event_type": "run_failed", "payload": {"trace_id": "tr1"}})
    assert r is not None and r.get("route") == "run_failed"

def test_invalid():
    assert handle_kirp_event({}) is None
    assert handle_kirp_event(None) is None
