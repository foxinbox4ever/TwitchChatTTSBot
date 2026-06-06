import websockets
import logging
logger = logging.getLogger(__name__)
import json
import asyncio

from core.config import load_settings

OBS_Bobble_image = load_settings("settings.json")["OBS_Bobble_image"]
connected_clients = set()


async def websocket_handler(websocket):
    connected_clients.add(websocket)
    try:
        logger.info("New client connected")
        await websocket.send(json.dumps({"imagePath": OBS_Bobble_image}))
        async for _ in websocket:
            pass
    finally:
        connected_clients.discard(websocket)
        logger.info("Client disconnected")


async def broadcast_message(username, message, duration, audio_b64=None, volume=1.0):
    is_sub = any(
        keyword in message.lower()
        for keyword in ("thank you very much for the sub!", "thank you very much for the gifted sub")
    )

    if not connected_clients:
        return

    payload = {
        "username": username.strip(),
        "message": message.strip(),
        "isSub": is_sub,
        "duration": duration,
        "volume": volume,
    }
    if audio_b64:
        payload["audio"] = audio_b64

    message_data = json.dumps(payload)
    logger.info(f"Broadcasting TTS: username={username!r}, message={message!r}")

    await asyncio.gather(*(client.send(message_data) for client in list(connected_clients)))


async def update_latest_message(username, message, duration, audio_b64=None, volume=1.0):
    try:
        await broadcast_message(username, message, duration, audio_b64, volume)
    except Exception as e:
        logger.error(f"Failed to send latest message: {e}")


async def broadcast_notification(notification_type, username, audio_b64=None):
    if not connected_clients:
        return
    payload = {"notification": {"type": notification_type, "username": username}}
    if audio_b64:
        payload["notification"]["audio"] = audio_b64
    data = json.dumps(payload)
    await asyncio.gather(*(client.send(data) for client in list(connected_clients)))


async def start_websocket_server():
    port = load_settings("settings.json").get("OBS_Websocket_Port", 8080)
    async with websockets.serve(websocket_handler, "0.0.0.0", port):
        logger.info(f"WebSocket server started on ws://0.0.0.0:{port}")
        await asyncio.Future()
