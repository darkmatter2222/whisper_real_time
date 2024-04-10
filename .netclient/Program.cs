using System;
using System.Net.WebSockets;
using System.Threading;
using System.Threading.Tasks;
using NAudio.Wave;

class Program
{
    private static ClientWebSocket websocketConnection = null;
    private static WaveInEvent waveIn = new WaveInEvent();
    private static byte[] audioBuffer;
    private static int bufferPosition = 0;
    private static readonly int bufferSizeInSeconds = 5;
    private static readonly int sampleRate = 16000; // Sample rate in Hz
    private static readonly int bitsPerSample = 16; // Bits per sample
    private static readonly int channels = 1; // Number of channels (1 for mono, 2 for stereo)

    static async Task Main(string[] args)
    {
        Console.CancelKeyPress += async (sender, e) =>
        {
            e.Cancel = true; // Prevent immediate termination
            await CleanupAsync();
        };

        Console.WriteLine("Starting WebSocket client for transcription...");
        await SetupMicrophoneAndWebSocket();

        // Keep the application running until interrupted
        await Task.Delay(Timeout.Infinite);
    }

    private static async Task SetupMicrophoneAndWebSocket()
    {
        websocketConnection = new ClientWebSocket();
        await websocketConnection.ConnectAsync(new Uri("ws://localhost:8765"), CancellationToken.None);

        // Calculate buffer size for 5 seconds of audio
        int bytesPerSample = bitsPerSample / 8;
        int bufferSize = sampleRate * bytesPerSample * channels * bufferSizeInSeconds;
        audioBuffer = new byte[bufferSize];

        waveIn.DeviceNumber = 0;
        waveIn.WaveFormat = new WaveFormat(sampleRate, bitsPerSample, channels);
        waveIn.DataAvailable += async (sender, e) =>
        {
            // Buffer incoming data until we have enough for 5 seconds
            int bytesToCopy = Math.Min(audioBuffer.Length - bufferPosition, e.BytesRecorded);
            Array.Copy(e.Buffer, 0, audioBuffer, bufferPosition, bytesToCopy);
            bufferPosition += bytesToCopy;

            if (bufferPosition >= audioBuffer.Length)
            {
                // Buffer is full, send data
                if (websocketConnection.State == WebSocketState.Open)
                {
                    await websocketConnection.SendAsync(new ArraySegment<byte>(audioBuffer), WebSocketMessageType.Binary, true, CancellationToken.None);
                }

                // Reset buffer position
                bufferPosition = 0;
            }
        };

        waveIn.StartRecording();
        Console.WriteLine("Microphone is recording. Press Ctrl+C to stop.");
    }

    private static async Task CleanupAsync()
    {
        Console.WriteLine("\nStopping and cleaning up...");

        waveIn.StopRecording();
        waveIn.Dispose();
        
        if (websocketConnection != null && websocketConnection.State == WebSocketState.Open)
        {
            await websocketConnection.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
        }

        Console.WriteLine("Cleanup completed. Exiting application.");
    }
}
