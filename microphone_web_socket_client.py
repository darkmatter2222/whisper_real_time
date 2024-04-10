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


import websockets

# Global variable to store the WebSocket connection
websocket_connection = None

# Async function to establish WebSocket connection
async def establish_websocket_connection(uri):
    return await websockets.connect(uri)

# Refactored WebSocket client function for continuous transmission
async def transcribe_with_websocket(audio_bytes, websocket):
    await websocket.send(audio_bytes)
    transcription = await websocket.recv()
    return transcription

# Function to manage the WebSocket connection and communication
async def manage_websocket_communication(audio_data):
    global websocket_connection
    try:
        if websocket_connection is None or websocket_connection.closed:
            websocket_connection = await establish_websocket_connection("wss://dym-cat.fiservcstaifactory.com:443")
        return await transcribe_with_websocket(audio_data, websocket_connection)
    except Exception as e:
        print(f"WebSocket error: {e}")
        return None

# Main function adaptation to handle continuous WebSocket connection
def handle_websocket_communication(audio_data):
    return asyncio.get_event_loop().run_until_complete(manage_websocket_communication(audio_data))


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
                for x in range(1):
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
