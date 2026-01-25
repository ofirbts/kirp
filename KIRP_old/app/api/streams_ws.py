# app/api/streams_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json

logger = logging.getLogger("StreamsWS")
router = APIRouter(prefix="/ws", tags=["StreamsWS"])


@router.websocket("/streams")
async def streams_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            logger.info(f"Received WS message: {data}")
            await ws.send_text(json.dumps({"status": "ok", "echo": data}))
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
