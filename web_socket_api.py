import asyncio
import websockets

async def audio_receiver(websocket, path):
    async for message in websocket:
        if isinstance(message, bytes):
            print(f"Received audio sample of size: {len(message)} bytes")
            # Respond to the client after receiving the audio sample
            await websocket.send("Got it")
        else:
            print("Received non-binary message")
            # Optionally, respond for non-binary messages as well
            await websocket.send("Expected binary data")

async def main():
    async with websockets.serve(audio_receiver, "localhost", 8765):
        await asyncio.Future()  # Run forever

asyncio.run(main())
