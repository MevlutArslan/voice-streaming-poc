from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager, get_eth0_ip
import asyncio
import transcriber
from llm import TranscriptionHandler, ChatModel, ModelResponseHandler
from reactivex import Subject
from typing import List
from starlette.websockets import WebSocketState
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
    
    response_handler = ModelResponseHandler()

    chat_model = ChatModel()
    
    
    async def should_model_respond(transcription_handler: TranscriptionHandler, transcription: str) -> tuple[bool, str]:
        print("Received Transcriptions from Sink: {}".format(transcription))
        model_should_respond, clean_transcription = await transcription_handler.run(transcription)
        return (model_should_respond, clean_transcription)

    async def handle_transcription(raw_transcription: str):
        if websocket.client_state != WebSocketState.CONNECTED:
            transcription_observable.dispose()
            return
        
        model_should_respond, transcription = await should_model_respond(transcription_handler= transcription_handler,
                                                                                   transcription= raw_transcription)
        
        if model_should_respond == False:
            return
        
        # if generating_response[0]:
        #     print("The model is already generating response, waiting...")
        #     return
        
        print("End of thought detected for: {}".format(transcription))
        transcriptions.clear()
        accumulated_tokens = []
        # generating_response = True
        async for token in chat_model.invoke(transcription):
            if token == None:
                # generating_response = False
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
                data = await asyncio.wait_for(websocket.receive_bytes(), 10)
                # data = await websocket.receive_bytes()
                if not dg_connection:
                    dg_connection = await transcriber.connect_to_deepgram(transcriptions, transcription_observable)
                    send_ping_task = asyncio.create_task(transcriber.send_ping(dg_connection))
                try:
                    if dg_connection:
                        await transcriber.send_data_deepgram(data, dg_connection)
                except Exception as e:
                    print(f"Failed to send data: {e}")
            except TimeoutError:
                # close the connection to the transcriber as Deepgram timesout when 
                # it doesn't receive audio data for 10 seconds
                print("Disconnected Deepgram after 10 seconds of inactivity.")
                if send_ping_task:
                    send_ping_task.cancel()
                if dg_connection:
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
