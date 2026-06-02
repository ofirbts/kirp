"""E2E: n8n workflow JSON name, nodes, connections, no orphans."""
import json
import os
from pathlib import Path

import pytest

BASE = Path(os.environ.get("BRAND_OS_V3_PATH", Path(__file__).resolve().parent.parent / "brand_os_v3"))
WORKFLOW_PATH = BASE / "n8n" / "brand_os_v3_workflow.json"


@pytest.fixture(scope="module")
def workflow() -> dict:
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_n8n_name_exists(workflow: dict) -> None:
    assert "name" in workflow
    assert isinstance(workflow["name"], str)


def test_n8n_nodes_exist(workflow: dict) -> None:
    assert "nodes" in workflow
    assert isinstance(workflow["nodes"], list)
    assert len(workflow["nodes"]) > 0


def test_n8n_connections_valid(workflow: dict) -> None:
    assert "connections" in workflow
    conn = workflow["connections"]
    assert isinstance(conn, dict)
    names = {n["name"] for n in workflow["nodes"]}
    for source, targets in conn.items():
        assert source in names, f"Connection source {source} not in nodes"
        for output_list in targets.get("main", []):
            for t in output_list:
                node = t.get("node")
                if node:
                    assert node in names, f"Connection target {node} not in nodes"


def test_n8n_no_orphan_nodes(workflow: dict) -> None:
    names = {n["name"] for n in workflow["nodes"]}
    conn = workflow.get("connections", {})
    referenced = set(conn.keys())
    for source, targets in conn.items():
        for output_list in targets.get("main", []):
            for t in output_list:
                referenced.add(t.get("node"))
    referenced.discard(None)
    for name in names:
        if name == "Manual Trigger":
            continue
        assert name in referenced, f"Orphan node: {name}"
