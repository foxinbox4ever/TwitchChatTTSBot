import websockets
import logging
import json
import asyncio
import time

from config import load_settings

OBS_Bobble_image = load_settings("settings.json")["OBS_Bobble_image"]
connected_clients = set()  # WebSocket clients set

# Start WebSocket server to handle real-time messaging
async def websocket_handler(websocket):
    connected_clients.add(websocket)
    try:
        logging.info("New client connected")

        # Send image path
        await websocket.send(json.dumps({
            "imagePath": OBS_Bobble_image
        }))

        # Listen for messages (if needed)
        async for _ in websocket:
            pass

    finally:
        connected_clients.remove(websocket)
        logging.info("Client disconnected")


# Broadcast function to send messages (and optionally vote) to all clients
async def broadcast_message(username, message, duration):
    is_sub = False

    sub_keywords = [
        "thank you very much for the sub!",
        "thank you very much for the gifted sub",
    ]

    if any(keyword in message.lower() for keyword in sub_keywords):
        is_sub = True

    if connected_clients:
        payload = {
            "username": username.strip(),
            "message": message.strip(),
            "isSub": is_sub,
            "duration": duration
        }

        message_data = json.dumps(payload)
        logging.info(f"Message payload: {message_data}")

        await asyncio.gather(*(client.send(message_data) for client in connected_clients))



async def update_latest_message(username, message, duration):
    logging.info("Sending latest message to WebSocket clients...")
    try:
        await broadcast_message(username, message, duration)
    except Exception as e:
        logging.error(f"Failed to send latest message: {e}")


async def start_websocket_server():
    async with websockets.serve(websocket_handler, "localhost", 8080):
        logging.info("WebSocket server started on ws://localhost:8080")
        await asyncio.Future()  # Run forever
