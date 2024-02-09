from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager, get_eth0_ip
import asyncio
from audio import is_audio_silent, save_audio_as_file, get_transcription
import numpy as np
import time
import io

app = FastAPI()
manager = ConnectionManager()

@app.websocket("/communicate")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    accumulated_bytes = io.BytesIO()
    audio_accumulation_threshold = 5.0
    audio_silence_threshold = 3.0
    
    accumulated_audio_len = 0.0
    audio_sent_by_client_len = 0.1 # this is a fact that I checked on the client
    try:
        while True:
            process_data = False
            try:
                # if we haven't received anything for audio_silence_threshold duration then we should
                # process the data in the buffer
                data = await asyncio.wait_for(websocket.receive_bytes(), audio_silence_threshold)
                
                accumulated_bytes.write(data)
                accumulated_audio_len += audio_sent_by_client_len
                
                if accumulated_audio_len >= audio_accumulation_threshold:
                    print("Received audio for the threshold amount, triggering execution")
                    process_data = True
            except asyncio.TimeoutError:
                # make sure the accumulated bytes arent empty:
                if accumulated_bytes.tell() > 0:
                    print("Did not receive audio for the threshold amount, triggering execution")
                    process_data = True
                
            if process_data:
                print("Processing Data...")
                accumulated_bytes.seek(0)
                
                # clear out the buffer
                accumulated_bytes.seek(0)
                accumulated_bytes.truncate(0)
                # -------------------------------
                accumulated_audio_len = 0.0
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
