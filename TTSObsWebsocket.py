import websockets
import logging
import json
import asyncio

from config import load_settings

OBS_Bobble_image = load_settings("settings.json")["OBS_Bobble_image"]
connected_clients = set() # WebSocket clients set

# Start WebSocket server to handle real-time messaging
async def websocket_handler(websocket, path):
    connected_clients.add(websocket)
    try:
        logging.info("New client connected")

        # Send image path initially on connection
        initial_message = json.dumps({
            "imagePath": OBS_Bobble_image  # Path to the image, e.g., "dwightHead.png"
        })
        logging.info(f"Sending initial message: {initial_message}")
        await websocket.send(initial_message)
        async for message in websocket:
            pass  # Handle any incoming messages here if needed
    finally:
        connected_clients.remove(websocket)
        logging.info("Client disconnected")

# Broadcast function to send a message to all WebSocket clients
async def broadcast_message(username, message, duration):
    if connected_clients:
        # Create a dictionary with the proper structure
        message_data = json.dumps({
            "username": username.strip(),  # Ensure there are no leading/trailing spaces
            "message": message.strip(),  # Ensure there are no leading/trailing spaces
            "duration": duration
        })
        await asyncio.wait([client.send(message_data) for client in connected_clients])

# Update function for WebSocket
async def update_latest_message(username, message, duration):
    logging.info("Sending latest message to WebSocket clients...")
    try:
        # Call broadcast_message with separate parameters
        await broadcast_message(username, message, duration)  # Send the updated message
    except Exception as e:
        logging.error(f"Failed to send latest message: {e}")

# Start the WebSocket server asynchronously
async def start_websocket_server():
    async with websockets.serve(websocket_handler, "localhost", 8080):
        logging.info("WebSocket server started on ws://localhost:8080")
        await asyncio.Future()  # Run forever
