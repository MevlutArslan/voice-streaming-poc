import aiortc
from fastapi import FastAPI
from fastapi.websockets import WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager, get_eth0_ip
import aiohttp
from typing import Dict

app = FastAPI()
connection_manager: ConnectionManager = ConnectionManager()
llm_server_sdp_endpoint = "http://10.0.0.61:8080/connections/answer"
llm_server_ice_endpoint = "http://10.0.0.61:8080/connections/ice_candidates"

@app.websocket("/offer")
async def offer(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            data: Dict = await websocket.receive_json(mode="binary")
            print("Received Data: {}".format(data))

            if "type" in data:
                async with aiohttp.ClientSession() as session:
                            async with session.post(llm_server_sdp_endpoint, json=data) as response:
                                response_data = await response.json()
                                # answer_obj = aiortc.RTCSessionDescription(sdp=response_data["sdp"], type="answer")
                                await websocket.send_json(response_data, mode="binary")
            else:
                 async with aiohttp.ClientSession() as session:
                            async with session.post(llm_server_ice_endpoint, json=data) as response:
                                response_data = await response.json()
                                # print(response_data.status)            
    except WebSocketDisconnect:
        print("Receieved WebSocketDisconnect Exception")

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="172.20.10.4", port=8999) # mobile hotspot
    uvicorn.run(app, host="10.0.0.61", port=8999) # home