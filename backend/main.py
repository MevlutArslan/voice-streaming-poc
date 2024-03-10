from fastapi import FastAPI, Request
from connection_manager import get_eth0_ip
import asyncio
import aiortc
from aiortc.rtcicetransport import Candidate, candidate_from_aioice
from webrtc_client import WebRtcClient
from transcription_utils import handle_audio_stream

app = FastAPI()
web_rtc_client = WebRtcClient(audio_stream_handler= handle_audio_stream) 

web_rtc_connection_has_been_closed = asyncio.Event()

@app.post("/connections/answer")
async def answer_signaling_server(request: Request):
    data = await request.json()
    sdp = data["sdp"]
    remote_peer_sdp = aiortc.RTCSessionDescription(sdp=sdp, type="offer")

    # Connect to the remote peer and generate an answer
    answer = await web_rtc_client.connect_to_connection(remote_peer_sdp)

    return answer

@app.post("/connections/ice_candidates")
async def register_ice_candidate(request: Request):
    data = await request.json()

    sdp = data.get("sdp", "")
    sdp_mline_index = data.get("sdpMLineIndex", 0)
    sdp_mid = data.get("sdpMid", "")

    candidate = Candidate.from_sdp(sdp)
    ice_candidate = candidate_from_aioice(candidate)
    ice_candidate.sdpMid = sdp_mid
    ice_candidate.sdpMLineIndex = sdp_mline_index

    await web_rtc_client.add_ice_candidate(ice_candidate)

if __name__ == "__main__":
    # ip_address = get_eth0_ip()
    ip_address = "10.0.0.61"
    if ip_address:
        print(f"Server is running at ws://{ip_address}:8999/communicate")
    else:
        print("Failed to retrieve IP address.")
    
    import uvicorn
    uvicorn.run(app, host=ip_address, port=8080)
