import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

websocket_router = APIRouter()

_connected_clients: list[WebSocket] = []


@websocket_router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    """General-purpose WebSocket for live updates."""
    await websocket.accept()
    _connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connected_clients.remove(websocket)


async def broadcast(message: dict) -> None:
    """Push a JSON message to every connected WebSocket client."""
    payload = json.dumps(message)
    for client in list(_connected_clients):
        try:
            await client.send_text(payload)
        except Exception:
            _connected_clients.remove(client)
