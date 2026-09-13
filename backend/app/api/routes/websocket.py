"""WebSocket endpoint for real-time simulation telemetry.

The endpoint deliberately uses the application's singleton WebSocketManager.
Having a second manager here used to split connection state and introduced
calls to methods that do not exist on the real manager.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...core.runtime import runtime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    room: Optional[str] = None,
):
    """Accept a client and keep it attached to the requested simulation room."""
    client_id = None
    manager = runtime.websocket_manager
    room_name = room or "global"
    # Frontend uses ?room=<sim_id>; the event bridge publishes to the
    # canonical `simulation:<sim_id>` room. Normalize here so both sides
    # always join the exact same room.
    canonical_room = (
        runtime.room_for_simulation(room_name)
        if room_name != "global" and not room_name.startswith("simulation:")
        else manager_room(room_name)
    )

    try:
        connection = await manager.connect(
            websocket,
            client_id=None,
            room=canonical_room,
        )
        client_id = connection["client_id"]

        # Send a single explicit ACK in addition to manager's established
        # message for compatibility with older dashboard clients.
        logger.info("🔗 WebSocket client %s connected to room %s (requested=%s)", client_id, canonical_room, room_name)

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"},
                })
                continue

            await manager.handle_message(client_id, message)

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket client %s disconnected", client_id)
    except Exception as exc:
        logger.exception("❌ WebSocket endpoint error for %s: %s", client_id, exc)
    finally:
        if client_id is not None:
            await manager.disconnect(client_id, code=1000, reason="Connection closed")


def manager_room(room: str) -> str:
    """Normalize room names without changing simulation IDs."""
    return room.strip() or "global"
