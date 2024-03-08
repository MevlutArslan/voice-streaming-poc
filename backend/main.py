from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from connection_manager import ConnectionManager, get_eth0_ip
import asyncio
import transcriber
from llm import TranscriptionHandler, ChatModel, ModelResponseHandler
from reactivex import Subject
from typing import List
from starlette.websockets import WebSocketState
import re
import aiortc
from aiortc.rtcicetransport import Candidate, candidate_from_aioice
import pyaudio
import av
from contextlib import asynccontextmanager
from deepgram import AsyncLiveClient
import signal

app = FastAPI()
manager = ConnectionManager()
remote_peer_sdp: aiortc.RTCSessionDescription = None
peer_connection: aiortc.RTCPeerConnection = None

receive_audio_task: asyncio.Task = None

web_rtc_connection_has_been_closed = asyncio.Event()

## CONSTANTS
MIN_WORD_COUNT = 16

async def should_model_respond(transcription_handler: TranscriptionHandler, transcription: str) -> tuple[bool, str]:
    model_should_respond, clean_transcription = await transcription_handler.run(transcription)
    return (model_should_respond, clean_transcription)

def combine_transcriptions(previous_transcription: str, current_transcription: str) -> str:
    ## TODO: Make an LLM do this
        ## TODO: [] Test if gpt 3.5 can handle this
    return previous_transcription + " " + current_transcription

async def invoke_chat_model(chat_model: ChatModel, transcription: str):
    accumulated_tokens = []
    async for token in chat_model.invoke(transcription):
        if token is None:
            break

        accumulated_tokens.append(token)

        if len(accumulated_tokens) >= MIN_WORD_COUNT:
            response = "".join(accumulated_tokens)
            print(response)
            # await handle_response(response)
            accumulated_tokens.clear()

    # Process or print any remaining tokens
    if accumulated_tokens:
        response = "".join(accumulated_tokens)
        print(response)
        # await handle_response(response)

async def cleanup_resources(send_ping_task: asyncio.Task, deepgram_conn: AsyncLiveClient, ongoing_invoke_chat_model_task: asyncio.Task):
    if send_ping_task:
        send_ping_task.cancel()
        send_ping_task = None
    if deepgram_conn:
        await transcriber.disconnect_deepgram(deepgram_conn)
        deepgram_conn = None
    if ongoing_invoke_chat_model_task:
        ongoing_invoke_chat_model_task.cancel()
        ongoing_invoke_chat_model_task = None
                
async def handle_audio_stream(track: aiortc.MediaStreamTrack):

    ## State
    deepgram_conn = None
    transcription_observable: Subject = Subject()
    transcriptions: List[str] = []
    send_ping_task: asyncio.Task = None
    generating_response = False
    model_should_respond_history = []
    ongoing_invoke_chat_model_task: asyncio.Task = None

    ## LLMs
    transcription_handler = TranscriptionHandler()
    # response_handler = ModelResponseHandler()
    chat_model = ChatModel()
        
    '''
    POSSIBLE SOLUTION TO FALSE 'model_should_respond' detections.
    
    When the should_model_respond() function returns true while the user is still talking should_model_respond() detects another end of thought,
    1. cancel the process
    2. combine the previous and current eot prompts
    3. feed it into the ChatModel
    '''

    # model_should_respond_history.append(transcription)
    async def handle_transcription(raw_transcription: str):
        nonlocal generating_response
        nonlocal ongoing_invoke_chat_model_task
        nonlocal model_should_respond_history
        
        # logging.debug("Querying should_model_respond")
        model_should_respond, transcription = await should_model_respond(transcription_handler= transcription_handler,
                                                                                transcription = raw_transcription)
        
        print("Model Should Respond: {}, Transcription: {}".format(model_should_respond, transcription))
        if model_should_respond == False:
            return
        
        if generating_response == True and ongoing_invoke_chat_model_task is not None: 
            # logging.debug("Detected a need to update the transcription")   
            ongoing_invoke_chat_model_task.cancel()
            transcription = combine_transcriptions(previous_transcription= model_should_respond_history[0], current_transcription=transcription)
            
        generating_response = True
        model_should_respond_history.append(transcription)
        
        print("🙄 invoking chat model")
        
        ongoing_invoke_chat_model_task = asyncio.create_task(invoke_chat_model(chat_model, transcription))
        # try:
        #     # logging.debug("Waiting for ongoing_invoke_chat_model_task")
        #     await ongoing_invoke_chat_model_task
        # except asyncio.CancelledError:
        #     print("Token processing task was canceled.")
        
        # logging.debug("Cleaning up after handle_transcription")

        ## Reset
        generating_response = False
        transcriptions.clear()
        model_should_respond_history.clear()
        ongoing_invoke_chat_model_task = None

    transcription_observable.subscribe(
        on_next=lambda transcription: asyncio.create_task(handle_transcription(transcription))
    )

    try:
        while not web_rtc_connection_has_been_closed.is_set():
            frame: av.AudioFrame = await track.recv()
            
            audio_data = frame.to_ndarray()[0]
            data = audio_data.tobytes()

            if not deepgram_conn:
                # logging.debug("Creating a connection to deepgram server")
                deepgram_conn = await transcriber.connect_to_deepgram(transcriptions, transcription_observable)
                # logging.debug("Starting send_ping_task")
                send_ping_task = asyncio.create_task(transcriber.send_ping(deepgram_conn))
            try:
                if deepgram_conn:
                    # print("Sending bytes to transcriber")
                    await transcriber.send_data_deepgram(data, deepgram_conn) 
            except Exception as e:
                print(f"Failed to send data: {e}")  
    except Exception as e:
        print("Received an exception: {}".format(e))
        cleanup_resources(send_ping_task=send_ping_task, deepgram_conn=deepgram_conn, ongoing_invoke_chat_model_task=
                          ongoing_invoke_chat_model_task)


@app.post("/connections/answer")
async def answer_signaling_server(request: Request):
    global remote_peer_sdp, peer_connection, receive_audio_task
    data = await request.json()
    sdp = data["sdp"]
    remote_peer_sdp = aiortc.RTCSessionDescription(sdp=sdp, type="offer")
    if peer_connection is None:
        peer_connection = aiortc.RTCPeerConnection()
        # peer_connection.addTrack(aiortc.MediaPlayer())

    @peer_connection.on("icegatheringstatechange")
    async def on_icegatheringstatechange():
        print("Ice Gather state changed: {}".format(peer_connection.iceGatheringState))

    @peer_connection.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state is %s", peer_connection.connectionState)
        if peer_connection.connectionState == "connected":
            print("Established connection between peers!")
            web_rtc_connection_has_been_closed.clear()
        elif peer_connection.connectionState == "closed":
            print("WebRTC connection has been closed.")
            web_rtc_connection_has_been_closed.set()
            receive_audio_task.cancel()
            # Clean up resources here (e.g., close the audio stream, terminate the task)
        elif peer_connection.connectionState == "failed":
            receive_audio_task.cancel()
            await peer_connection.close()

    @peer_connection.on("track")
    async def on_track(track: aiortc.MediaStreamTrack):
        global receive_audio_task
        if track.kind == "audio":
            print("Received audio track")
            receive_audio_task = asyncio.create_task(handle_audio_stream(track))

        @track.on("ended")
        async def on_ended():
            print("Audio Track ended")
            receive_audio_task.cancel()


    await peer_connection.setRemoteDescription(remote_peer_sdp)
    answer = await peer_connection.createAnswer()
    await peer_connection.setLocalDescription(answer)
    
    return answer

@app.post("/connections/ice_candidates")
async def register_ice_candidate(request: Request):
    global remote_peer_sdp, peer_connection

    data = await request.json()

    sdp = data.get("sdp", "")
    sdp_mline_index = data.get("sdpMLineIndex", 0)
    sdp_mid = data.get("sdpMid", "")

    candidate = Candidate.from_sdp(sdp)
    # Create the RTCIceCandidate object
    ice_candidate = candidate_from_aioice(candidate)
    ice_candidate.sdpMid = sdp_mid
    ice_candidate.sdpMLineIndex = sdp_mline_index

    await peer_connection.addIceCandidate(ice_candidate)

if __name__ == "__main__":
    # ip_address = get_eth0_ip()
    ip_address = "10.0.0.61"
    if ip_address:
        print(f"Server is running at ws://{ip_address}:8999/communicate")
    else:
        print("Failed to retrieve IP address.")
    
    import uvicorn
    uvicorn.run(app, host=ip_address, port=8080)
