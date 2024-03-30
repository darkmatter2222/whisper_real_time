#! python3.7

import asyncio
import websockets
import numpy as np
import torch
from faster_whisper import WhisperModel  # Importing faster_whisper

device = torch.device('cuda')
print(torch.cuda.is_available())  # Returns True if GPU is available
print(torch.cuda.device_count())  # Number of available GPUs
print(torch.cuda.current_device())  # Device number of the active GPU (e.g., 0)

from datetime import datetime

# Load Whisper model (you might want to adjust the model size based on your needs)
model_size = "base"  # You can adjust this as needed
# Adjust model loading for faster_whisper with appropriate compute_type
audio_model = WhisperModel(model_size, device="cuda", compute_type="float16")

async def transcribe_audio(audio_bytes):
    """Transcribe the given audio bytes using Whisper model."""
    # Convert data from 16 bit wide integers to floating point with a width of 32 bits.
    # Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    # Transcribe the audio
    segments, info = audio_model.transcribe(audio_np, beam_size=5)
    # Constructing the full transcription text from segments
    text = ' '.join([segment.text for segment in segments]).strip()
    print(f"Detected language '{info.language}' with probability {info.language_probability}")
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
