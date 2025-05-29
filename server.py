import asyncio
from typing import Any
import websockets
import json

# Simple token-based authentication
VALID_TOKENS: dict[str, str] = {
    "controller": "ctrl123",
    "contestant": "cont123",
    "host": "host123",
    "tvscreen": "tv123",
    "audience": "aud123",
}

# Store connections
clients_by_role: dict[str, set[websockets.ServerConnection]] = {
    "controller": set(),
    "contestant": set(),
    "host": set(),
    "tvscreen": set(),
    "audience": set(),
}


async def register(websocket: websockets.ServerConnection) -> None:
    try:
        # Initial handshake
        data: str = await websocket.recv()
        msg: dict[str, Any] = json.loads(data)

        role: str = msg.get("role")
        token: str = msg.get("token")

        if role not in VALID_TOKENS:
            await websocket.send(json.dumps({"error": "Unknown role"}))
            return

        if token != VALID_TOKENS[role]:
            await websocket.send(json.dumps({"error": "Invalid token"}))
            return

        clients_by_role[role].add(websocket)
        print(f"{role.capitalize()} connected")

        await listen(websocket)

    except websockets.ConnectionClosed:
        print("Connection closed")
    finally:
        for role_set in clients_by_role.values():
            role_set.discard(websocket)


async def listen(websocket: websockets.ServerConnection) -> None:
    async for message in websocket:
        try:
            msg: dict[str, Any] = json.loads(message)
            if websocket in clients_by_role["controller"]:
                roles: list[str] | None = msg.get("roles")
                payload: Any = msg.get("message")
                await send_to_roles(payload, roles)
            else:
                await websocket.send(
                    json.dumps({"error": "Only controllers can send messages"})
                )
        except json.JSONDecodeError:
            await websocket.send(json.dumps({"error": "Invalid JSON"}))


async def send_to_roles(message: Any, roles: list[str] | None) -> None:
    async def send(ws: websockets.ServerConnection, message: Any):
        await ws.send(json.dumps({"type": "message", "message": message}))

    if roles is None:
        for role, clients in clients_by_role.items():
            for ws in clients:
                await send(ws=ws, message=message)
        return

    for role in roles:
        role_set: set[websockets.ServerConnection] = clients_by_role.get(role, set())
        for ws in role_set:
            send(ws=ws, message=message)


async def main() -> None:
    async with websockets.serve(register, "localhost", 6789):
        print("WebSocket server started on ws://localhost:6789")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
