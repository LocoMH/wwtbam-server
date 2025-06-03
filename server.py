import asyncio
import websockets
import json

# Use the updated ServerConnection type
from websockets.server import ServerConnection

# Simple token-based authentication
VALID_TOKENS: dict[str, str] = {
    "controller": "ctrl123",
    "contestant": "cont123",
    "host": "host123",
    "tvscreen": "tv123",
    "audience": "aud123",
}

# Store connections
clients_by_role: dict[str, set[ServerConnection]] = {
    "controller": set(),
    "contestant": set(),
    "host": set(),
    "tvscreen": set(),
    "audience": set(),
}

# Track role by websocket for dynamic reassignment
websocket_roles: dict[ServerConnection, str] = {}


async def register(websocket: ServerConnection) -> None:
    try:
        data: str = await websocket.recv()
        msg: dict[str, object] = json.loads(data)
        await handle_registration(websocket, msg)
        await listen(websocket)
    except websockets.ConnectionClosed:
        print("Connection closed")
    finally:
        unregister(websocket)


async def handle_registration(
    websocket: ServerConnection, msg: dict[str, object]
) -> None:
    role: str = msg.get("role")
    token: str = msg.get("token")

    if role not in VALID_TOKENS:
        await websocket.send(json.dumps({"error": "Unknown role"}))
        return

    if token != VALID_TOKENS[role]:
        await websocket.send(json.dumps({"error": "Invalid token"}))
        return

    unregister(websocket)

    clients_by_role[role].add(websocket)
    print(f"{role.capitalize()} connected")

    websocket_roles[websocket] = role


async def listen(websocket: ServerConnection) -> None:
    async for message in websocket:
        print(f"Received message: {message}")
        try:
            msg: dict[str, object] = json.loads(message)
            if "role" in msg and "token" in msg:
                await handle_registration(websocket, msg)
                continue

            sender_role = websocket_roles.get(websocket)
            if sender_role == "controller":
                roles: list[str] = msg.get("roles")
                payload: object = msg.get("message")
                await send_to_roles(payload, roles)
            else:
                await websocket.send(
                    json.dumps({"error": "Only controllers can send messages"})
                )
        except json.JSONDecodeError:
            await websocket.send(json.dumps({"error": "Invalid JSON"}))


async def send_to_roles(message: object, roles: list[str] | None) -> None:
    if not roles:
        roles = list(clients_by_role.keys())
    for role in roles:
        role_set: set[ServerConnection] = clients_by_role.get(role, set())
        for ws in role_set:
            await ws.send(json.dumps({"type": "message", "message": message}))


def unregister(websocket: ServerConnection) -> None:
    for role_set in clients_by_role.values():
        role_set.discard(websocket)
    websocket_roles.pop(websocket, None)


async def main() -> None:
    async with websockets.serve(register, "localhost", 6789):
        print("WebSocket server started on ws://localhost:6789")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
