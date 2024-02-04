from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager, get_eth0_ip
from typing import List
import time
import asyncio
from io import BytesIO
app = FastAPI()
manager = ConnectionManager()

import pyaudio
from audio import is_audio_silent, save_audio_as_file, get_transcription

audio_manager = pyaudio.PyAudio()

# DISCLAIMER: Ideally you would send these from the client right 
#             before you open the stream instead of hardcoding it.
# Hardcoded audio parameters
rate = 48000
channels = 1
format = pyaudio.paFloat32

import numpy as np
# Create PyAudio stream with hardcoded parameters
# stream = audio_manager.open(rate=rate, channels=channels, format=format, output=True)

@app.websocket("/communicate")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    counter = 1
    accumulated_audio = np.array([], dtype=np.float32)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=2)
                # turn bytes object into a np array of type float32
                audio_chunk = np.frombuffer(data, dtype=np.float32)
                # accumulate the arrays
                accumulated_audio = np.concatenate((accumulated_audio, audio_chunk))
            except asyncio.TimeoutError:
                print("Detected prolonged silence!")
                if len(accumulated_audio) > 0:
                    audio_file_path = save_audio_as_file(accumulated_audio)
                    print(f"SAVED FILE TO {audio_file_path}")
                    text = get_transcription(audio_file_path)
                    print(text)
                    accumulated_audio = np.array([], dtype=np.float32)
                continue

            # is_silent = is_audio_silent(data, threshold=1.0)

            # if is_silent:
            #     # Check if silence exceeds 2 seconds
            #     current_time = time.time()
            #     if current_time - last_non_silent_time > 2:
            #         audio_file_path = save_audio_as_file(accumulated_audio)
            #         transcription = get_transcription(audio_file_path)
            #         print(transcription)
            #         accumulated_audio.clear()
            # else:
            #     last_non_silent_time = time.time()
            #     accumulated_audio.append(data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        # Clean up resources, stop the stream, and close it
        manager.disconnect(websocket)

if __name__ == "__main__":
    ip_address = get_eth0_ip()
    if ip_address:
        print(f"Server is running at ws://{ip_address}:8999/communicate")
    else:
        print("Failed to retrieve IP address.")
    
    import uvicorn
    uvicorn.run(app, host=ip_address, port=8999)
