#! python3.7

import asyncio
import websockets
import numpy as np
import whisper
import torch
device = torch.device('cuda')
print(torch.cuda.is_available())  # Returns True if GPU is available
print(torch.cuda.device_count())  # Number of available GPUs
print(torch.cuda.current_device())  # Device number of the active GPU (e.g., 0)

from datetime import datetime

# Load Whisper model (you might want to adjust the model size based on your needs)
model_size = "small"  # You can adjust this as needed
audio_model = whisper.load_model(model_size)

async def transcribe_audio(audio_bytes):
    """Transcribe the given audio bytes using Whisper model."""
    # Convert data from 16 bit wide integers to floating point with a width of 32 bits.
    # Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    # Transcribe the audio
    result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available())
    text = result['text'].strip()
    return text

async def audio_receiver(websocket, path):
    async for message in websocket:
        if isinstance(message, bytes):
            print(f"Received audio sample of size: {len(message)} bytes")
            # Transcribe the received audio
            transcribed_text = await transcribe_audio(message)
            # Respond to the client with the transcribed text
            await websocket.send(transcribed_text)
            print(f"Transcribed text: {transcribed_text}")
        else:
            print("Received non-binary message")
            # Optionally, respond for non-binary messages as well
            await websocket.send("Expected binary data")

async def main():
    async with websockets.serve(audio_receiver, "localhost", 8765):
        print("WebSocket server started. Listening on ws://localhost:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
