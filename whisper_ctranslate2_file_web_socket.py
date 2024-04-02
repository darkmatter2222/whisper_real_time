import asyncio
import websockets

# WebSocket client function to send audio data and receive transcription
async def transcribe_with_websocket(audio_bytes):
    uri = "wss://dym-cat.fiservcstaifactory.com:443"  # Assuming the WebSocket server is running on this URI
    async with websockets.connect(uri) as websocket:
        await websocket.send(audio_bytes)
        transcription = await websocket.recv()
        return transcription

# Function to read audio data from file and send for transcription
async def process_audio_file_and_transcribe(file_path):
    with open(file_path, "rb") as file:
        for line in file:
            transcription = await transcribe_with_websocket(line.strip())
            print(transcription)

# Main function to run the asyncio event loop
def main():
    file_path = "recorded_audio_data.txt"
    asyncio.run(process_audio_file_and_transcribe(file_path))

if __name__ == "__main__":
    main()
