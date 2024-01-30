import socket
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager


app = FastAPI()
manager = ConnectionManager()

def get_eth0_ip():
    import subprocess
    import re
    try:
        # Run the shell command to get IP address of eth0
        result = subprocess.run(['ip', 'addr', 'show', 'eth0'], capture_output=True, text=True, check=True)

        # Use regex to extract the IP address
        ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
        if ip_match:
            return ip_match.group(1)
        else:
            return None

    except subprocess.CalledProcessError:
        return None


@app.websocket("/communicate")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.send_personal_message("Bye!!!", websocket)

if __name__ == "__main__":
    ip_address = get_eth0_ip()
    if ip_address:
        print(f"Server is running at ws://{ip_address}:8000/communicate")
    else:
        print("Failed to retrieve IP address.")
    
    import uvicorn
    uvicorn.run(app, host=ip_address, port=8000)
