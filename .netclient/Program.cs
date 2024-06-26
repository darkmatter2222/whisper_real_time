﻿using System;
using System.Net.WebSockets;
using System.Text;
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
    private static readonly int channels = 1; // Mono
    private static readonly float EnergyThreshold = 0.001f; // Adjust this threshold based on testing and requirements

    static async Task Main(string[] args)
    {
        Console.CancelKeyPress += async (sender, e) =>
        {
            e.Cancel = true; // Prevent immediate termination
            await CleanupAsync();
        };

        Console.WriteLine("Starting WebSocket client for transcription...");
        await SetupMicrophoneAndWebSocket();

        // Start the task to listen for messages from the WebSocket
        var listeningTask = ListenForWebSocketResponses();

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
                // Check if the energy level of the buffer exceeds the threshold before sending
                if (CalculateEnergy(audioBuffer) > EnergyThreshold)
                {
                    if (websocketConnection.State == WebSocketState.Open)
                    {
                        await websocketConnection.SendAsync(new ArraySegment<byte>(audioBuffer), WebSocketMessageType.Binary, true, CancellationToken.None);
                        Console.WriteLine("Audio sent to server.");
                    }
                }
                else
                {
                    Console.WriteLine("Audio energy below threshold. Not sending.");
                }

                // Reset buffer position
                bufferPosition = 0;
            }
        };

        waveIn.StartRecording();
        Console.WriteLine("Microphone is recording. Press Ctrl+C to stop.");
    }

    private static async Task ListenForWebSocketResponses()
    {
        var buffer = new byte[4096*20];
        try
        {
            while (websocketConnection.State == WebSocketState.Open)
            {
                var result = await websocketConnection.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                if (result.MessageType == WebSocketMessageType.Text)
                {
                    var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    Console.WriteLine($"Response from server: {message}");
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"An exception occurred while listening for WebSocket responses: {ex.Message}");
        }
    }

    private static float CalculateEnergy(byte[] buffer)
    {
        double sum = 0;
        // Assuming 16-bit audio
        for (int i = 0; i < buffer.Length; i += 2)
        {
            short sample = (short)((buffer[i + 1] << 8) | buffer[i]);
            sum += sample * sample;
        }
        double rms = Math.Sqrt(sum / (buffer.Length / 2));
        return (float)(rms / short.MaxValue);
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
