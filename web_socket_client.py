import asyncio
import websockets
import os

async def send_audio_sample(uri, file_path):
    async with websockets.connect(uri) as websocket:
        # Read audio file in binary mode
        with open(file_path, "rb") as audio_file:
            audio_data = audio_file.read()
            await websocket.send(audio_data)
            print(f"Sent audio sample of size: {len(audio_data)} bytes")

            # Wait for a response from the server and print it
            response = await websocket.recv()
            print(f"Server response: {response}")

# The URI of the WebSocket server
server_uri = "ws://localhost:8765"

# Path to an audio file you want to send (update this path to your audio file)
audio_file_path = r"\\databrick\Active Server Drive\Audio\cat-meow-6226.mp3"

# Run the client and send an audio file
asyncio.run(send_audio_sample(server_uri, audio_file_path))
