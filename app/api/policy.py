from fastapi import APIRouter
import json

router = APIRouter()

@router.get("/")
def get_policy():
    return json.load(open("policies.json"))

@router.post("/")
def update_policy(data: dict):
    json.dump(data, open("policies.json", "w"), indent=2)
    return {"status": "updated"}
