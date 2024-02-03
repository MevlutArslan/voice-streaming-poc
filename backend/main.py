
def get_eth0_ip():
    import socket
    try:
        # Get the host name of the machine
        host_name = socket.gethostname()
        # Get the IP address of the machine
        ip_address = socket.gethostbyname(host_name)
        return ip_address
    except socket.error:
        return None

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager

app = FastAPI()
manager = ConnectionManager()

import pyaudio
from audio import is_audio_silent

audio_manager = pyaudio.PyAudio()

# DISCLAIMER: Ideally you would send these from the client right 
#             before you open the stream and not hard code it.
# Hardcoded audio parameters
rate = 48000
channels = 1
format = pyaudio.paFloat32

# Create PyAudio stream with hardcoded parameters
stream = audio_manager.open(rate=rate, channels=channels, format=format, output=True)

@app.websocket("/communicate")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_bytes()
            is_silent = is_audio_silent(data, threshold=1.0)
            if is_silent == False:
                stream.write(data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        stream.stop_stream()
        stream.close()


if __name__ == "__main__":
    ip_address = get_eth0_ip()
    if ip_address:
        print(f"Server is running at ws://{ip_address}:8999/communicate")
    else:
        print("Failed to retrieve IP address.")
    
    import uvicorn
    uvicorn.run(app, host=ip_address, port=8999)
