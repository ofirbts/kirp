import json
import os
from pathlib import Path
import pytest
import yaml

BASE = Path(os.environ.get("BRAND_OS_V3_PATH", Path(__file__).resolve().parent.parent / "brand_os_v3"))

def test_config_json():
    for p in (BASE / "config").glob("*.json"):
        with open(p) as f:
            assert isinstance(json.load(f), (dict, list))

def test_agents_json():
    for p in (BASE / "agents").glob("*.json"):
        with open(p) as f:
            d = json.load(f)
            assert isinstance(d, dict)

def test_workflow_json():
    for p in (BASE / "workflow").glob("*.json"):
        with open(p) as f:
            assert isinstance(json.load(f), dict)

def test_execution_json():
    for p in (BASE / "execution").glob("*.json"):
        with open(p) as f:
            assert isinstance(json.load(f), dict)

def test_kirp_yaml():
    for p in (BASE / "kirp").glob("*.yaml"):
        with open(p) as f:
            assert yaml.safe_load(f) is not None
