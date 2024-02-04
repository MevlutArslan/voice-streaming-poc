from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager, get_eth0_ip
import asyncio
from audio import is_audio_silent, save_audio_as_file, get_transcription
import numpy as np

app = FastAPI()
manager = ConnectionManager()

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
