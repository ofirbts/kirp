from fastapi import APIRouter
import json
from threading import Lock

router = APIRouter()
_lock = Lock()
POLICY_FILE = "policies.json"

@router.get("/")
def get_policy():
    with _lock:
        return json.load(open(POLICY_FILE))

@router.post("/")
def update_policy(data: dict):
    with _lock:
        json.dump(data, open(POLICY_FILE, "w"), indent=2)
