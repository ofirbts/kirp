"""
LinkedIn API v2 integration for Brand OS v3.
Posts text or image+text. Requires LINKEDIN_ACCESS_TOKEN and optionally LINKEDIN_PERSON_URN.
"""

import os
import urllib.request
import urllib.error
import json
from typing import Optional


def _get_token() -> Optional[str]:
    return os.environ.get("LINKEDIN_ACCESS_TOKEN")


def _get_person_urn() -> str:
    return os.environ.get("LINKEDIN_PERSON_URN", "urn:li:person:me")


def _api_request(method: str, url: str, data: Optional[dict] = None) -> dict:
    token = _get_token()
    if not token:
        return {"ok": False, "error": "LINKEDIN_ACCESS_TOKEN not set"}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"ok": True, "status": resp.status, "data": json.loads(resp.read().decode()) if resp.length else {}}
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
        except Exception:
            body = ""
        return {"ok": False, "error": body or str(e), "status": e.code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def post_text(content: str) -> dict:
    """
    Post text-only to LinkedIn (API v2 UGC post).
    content: Post body text.
    Returns dict with ok, id/error.
    """
    token = _get_token()
    if not token:
        return {"ok": False, "error": "LINKEDIN_ACCESS_TOKEN not set"}
    person_urn = _get_person_urn()
    url = "https://api.linkedin.com/v2/ugcPosts"
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    return _api_request("POST", url, payload)


def post_image(content: str, image_prompt: str) -> dict:
    """
    Post image + text to LinkedIn (API v2).
    content: Post body text.
    image_prompt: Used for alt text / description; actual image must be uploaded via Assets API first.
    Returns dict with ok, id/error. For full image flow you must register an asset and pass asset URN.
    """
    token = _get_token()
    if not token:
        return {"ok": False, "error": "LINKEDIN_ACCESS_TOKEN not set"}
    person_urn = _get_person_urn()
    asset_urn = os.environ.get("LINKEDIN_ASSET_URN")
    if not asset_urn:
        return {"ok": False, "error": "LINKEDIN_ASSET_URN not set; register image via Assets API first"}
    url = "https://api.linkedin.com/v2/ugcPosts"
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "IMAGE",
                "media": [{"status": "READY", "media": asset_urn, "title": {"text": image_prompt[:200]}}],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    return _api_request("POST", url, payload)
