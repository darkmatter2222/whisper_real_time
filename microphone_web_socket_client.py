#! python3.7

import argparse
import asyncio
import os
import numpy as np
import speech_recognition as sr
import websockets
from datetime import datetime, timedelta
from queue import Queue, Empty
from time import sleep
from sys import platform


# WebSocket client function to send audio data and receive transcription
async def transcribe_with_websocket(audio_bytes):
    uri = "ws://localhost:8765"  # Assuming the WebSocket server is running on this URI
    async with websockets.connect(uri) as websocket:
        await websocket.send(audio_bytes)
        transcription = await websocket.recv()
        return transcription


# Function to handle WebSocket communication (to be called within the main loop)
def handle_websocket_communication(audio_data):
    try:
        return asyncio.get_event_loop().run_until_complete(transcribe_with_websocket(audio_data))
    except Exception as e:
        print(f"WebSocket error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--energy_threshold", default=1000, help="Energy level for mic to detect.", type=int)
    parser.add_argument("--record_timeout", default=2, help="How real time the recording is in seconds.", type=float)
    parser.add_argument("--phrase_timeout", default=3,
                        help="How much empty space between recordings before we consider it a new line in the transcription.",
                        type=float)
    if 'linux' in platform:
        parser.add_argument("--default_microphone", default='pulse',
                            help="Default microphone name for SpeechRecognition. Run this with 'list' to view available Microphones.",
                            type=str)
    args = parser.parse_args()

    phrase_time = None
    data_queue = Queue()
    recorder = sr.Recognizer()
    recorder.energy_threshold = args.energy_threshold
    recorder.dynamic_energy_threshold = False

    # Microphone setup
    if 'linux' in platform:
        mic_name = args.default_microphone
        if not mic_name or mic_name == 'list':
            print("Available microphone devices are: ")
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                print(f"Microphone with name \"{name}\" found")
            return
        else:
            source = next((sr.Microphone(sample_rate=16000, device_index=index) for index, name in
                           enumerate(sr.Microphone.list_microphone_names()) if mic_name in name), None)
            if source is None:
                print(f"No microphone matching '{mic_name}' found.")
                return
    else:
        source = sr.Microphone(sample_rate=16000)

    record_timeout = args.record_timeout
    phrase_timeout = args.phrase_timeout
    transcription = ['']

    with source:
        recorder.adjust_for_ambient_noise(source)

    def record_callback(_, audio: sr.AudioData) -> None:
        data = audio.get_raw_data()
        data_queue.put(data)

    recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)
    print("Ready to transcribe.")

    while True:
        try:
            now = datetime.utcnow()
            if not data_queue.empty():
                phrase_complete = False
                if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                    phrase_complete = True
                phrase_time = now

                audio_data = b''.join(list(data_queue.queue))
                data_queue.queue.clear()

                # WebSocket communication for transcription
                text = handle_websocket_communication(audio_data)
                if text is not None:
                    print(text)
                else:
                    print("Error receiving transcription.")
            else:
                sleep(0.25)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
