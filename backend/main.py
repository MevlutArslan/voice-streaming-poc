from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager, get_eth0_ip
import asyncio
import transcriber
from audio import float32_to_linear16_bytes
from llm import TranscriptionHandler, generate_response, ModelResponseHandler
import threading
from reactivex import Subject, Observer, Observable, create
import reactivex.operators as ops
from typing import List
from starlette.websockets import WebSocketState
# from audio import TranscriptionSink
from openai import AsyncOpenAI
import re

app = FastAPI()
manager = ConnectionManager()

@app.websocket("/communicate")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    dg_connection = None
    send_ping_task: asyncio.Task = None

    transcription_observable: Subject = Subject()
    transcription_handler = TranscriptionHandler()
    transcriptions: List[str] = []
    
    response_client = AsyncOpenAI()
    response_handler = ModelResponseHandler()

    async def has_detected_end_of_thought(transcription_handler: TranscriptionHandler, transcription: str) -> tuple[bool, str]:
        print("Received Transcriptions from Sink: {}".format(transcription))
        end_of_thought_detected, clean_transcription = await transcription_handler.run(transcription)
        return (end_of_thought_detected, clean_transcription)

    async def handle_transcription(raw_transcription: str):
        if websocket.client_state != WebSocketState.CONNECTED:
            transcription_observable.dispose()
            return
        
        end_of_thought_detected, transcription = await has_detected_end_of_thought(transcription_handler= transcription_handler,
                                                                                   transcription= raw_transcription)
        
        if end_of_thought_detected == False:
            return

        print("End of thought detected for: {}".format(transcription))
        transcriptions.clear()
        accumulated_tokens = []
        async for token in generate_response(response_client, transcription):
            if token == None:
                continue
            
            accumulated_tokens.append(token)
            if re.match(r'[.!?]', token):
                should_return_response, response_text = await response_handler.run(accumulated_tokens)
                
                if should_return_response == False:
                    continue
                
                print(response_text)
                accumulated_tokens.clear()
            
            
    transcription_observable.subscribe(
        on_next=lambda transcription: asyncio.create_task(handle_transcription(transcription))
    )
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), 3)
                if not dg_connection:
                    dg_connection = await transcriber.connect_to_deepgram(transcriptions, transcription_observable)
                    send_ping_task = asyncio.create_task(transcriber.send_ping(dg_connection))

                try:
                    if dg_connection:
                        # NOTE: we only need this because the client sends float32 buffers, 
                        #       which will be changed on the client side to get rid of this
                        # int16_audio = float32_to_linear16_bytes(accumulated_bytes)
                        
                        await transcriber.send_data_deepgram(data, dg_connection)
                except Exception as e:
                    print(f"Failed to send data: {e}")
            except TimeoutError:
                # close the connection to the transcriber as Deepgram timesout when 
                # it doesn't receive audio data for 12 seconds
                await transcriber.disconnect_deepgram(dg_connection)
                dg_connection = None
    except WebSocketDisconnect:
        # Clean up resources, stop the stream, and close it
        manager.disconnect(websocket)
        if send_ping_task:
                send_ping_task.cancel()
        if dg_connection:
            await transcriber.disconnect_deepgram(dg_connection)
            dg_connection = None
        
if __name__ == "__main__":
    ip_address = get_eth0_ip()
    if ip_address:
        print(f"Server is running at ws://{ip_address}:8999/communicate")
    else:
        print("Failed to retrieve IP address.")
    
    import uvicorn
    uvicorn.run(app, host=ip_address, port=8999)
