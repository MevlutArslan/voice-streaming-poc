from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager, get_eth0_ip
import asyncio
import transcriber
from llm import TranscriptionHandler, ChatModel, ModelResponseHandler
from reactivex import Subject
from typing import List
from starlette.websockets import WebSocketState
import re

import logging

# Configure logging
# logging.basicConfig(level=logging.DEBUG,  # Set the # logging level
#                     format='%(asctime)s - %(levelname)s - %(message)s',  # Set the log message format
#                     filename='app.log',  # Specify the log file
#                     filemode='a')  # Specify the mode for opening the log file ('a' for append)

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
    
    generating_response = False
    model_should_respond_history = []
    
    ongoing_invoke_chat_model_task: asyncio.Task = None
    
    async def should_model_respond(transcription_handler: TranscriptionHandler, transcription: str) -> tuple[bool, str]:
        model_should_respond, clean_transcription = await transcription_handler.run(transcription)
        return (model_should_respond, clean_transcription)
    
    '''
    POSSIBLE SOLUTION TO FALSE 'model_should_respond' detections.
    
    When the should_model_respond() function returns true while the user is still talking should_model_respond() detects another end of thought,
    1. cancel the process
    2. combine the previous and current eot prompts
    3. feed it into the ChatModel
    '''
    
    async def invoke_chat_model(accumulated_tokens: List[str], transcription: str):
        # logging.debug("Called invoke_chat_model")
        async for token in chat_model.invoke(transcription):
            if token == None:
                continue
            accumulated_tokens.append(token)
            # logging.debug("Running the regular expression condition in invoke_chat_model")
            if re.match(r'[.!?]', token):
                should_return_response, response_text = await response_handler.run(accumulated_tokens)
                # logging.debug("Received response from chat_model.invoke")
                if should_return_response == False:
                    continue
            
                print(response_text)
                accumulated_tokens.clear()
                
    def combine_transcriptions(previous_transcription: str, current_transcription: str) -> str:
        ## TODO: Make an LLM do this
            ## TODO: [] Test if gpt 3.5 can handle this
        return previous_transcription + " " + current_transcription
        
    # model_should_respond_history.append(transcription)
    async def handle_transcription(raw_transcription: str):
        nonlocal generating_response
        nonlocal ongoing_invoke_chat_model_task
        nonlocal model_should_respond_history
        
        if websocket.client_state != WebSocketState.CONNECTED:
            transcription_observable.dispose()
            return
        
        # logging.debug("Querying should_model_respond")
        model_should_respond, transcription = await should_model_respond(transcription_handler= transcription_handler,
                                                                                transcription = raw_transcription)
        
        print("Model Should Respond: {}, Transcription: {}".format(model_should_respond, transcription))
        if model_should_respond == False:
            return
        
        print("End of thought detected for: {}".format(transcription))

        # if model_should_respond == True && 
        if generating_response == True and ongoing_invoke_chat_model_task is not None: 
            # logging.debug("Detected a need to update the transcription")   
            ongoing_invoke_chat_model_task.cancel()
            transcription = combine_transcriptions(previous_transcription= model_should_respond_history[0], current_transcription=transcription)
            
        generating_response = True
        model_should_respond_history.append(transcription)
        
        accumulated_tokens = []
        ongoing_invoke_chat_model_task = asyncio.create_task(invoke_chat_model(accumulated_tokens, transcription))
        try:
            # logging.debug("Waiting for ongoing_invoke_chat_model_task")
            await ongoing_invoke_chat_model_task
        except asyncio.CancelledError:
            print("Token processing task was canceled.")
                        
        # logging.debug("Cleaning up after handle_transcription")
        generating_response = False
        transcriptions.clear()
        model_should_respond_history.clear()
        ongoing_invoke_chat_model_task = None

    
    transcription_observable.subscribe(
        on_next=lambda transcription: asyncio.create_task(handle_transcription(transcription))
    )
    
    try:
        while True:
            data = await websocket.receive_bytes()
            # logging.debug("Received new bytes from the client")
            
            if not dg_connection:
                # logging.debug("Creating a connection to deepgram server")
                dg_connection = await transcriber.connect_to_deepgram(transcriptions, transcription_observable)
                # logging.debug("Starting send_ping_task")
                send_ping_task = asyncio.create_task(transcriber.send_ping(dg_connection))
            try:
                if dg_connection:
                    # logging.debug("Sending bytes to transcriber")
                    await transcriber.send_data_deepgram(data, dg_connection)
            except Exception as e:
                print(f"Failed to send data: {e}")  
    except WebSocketDisconnect:
        # logging.debug("Detected disconnect, cleaning up websocket")
        # Clean up resources, stop the stream, and close it
        manager.disconnect(websocket)
        if send_ping_task:
                send_ping_task.cancel()
        if dg_connection:
            await transcriber.disconnect_deepgram(dg_connection)
            dg_connection = None


# try:
                # data = await asyncio.wait_for(websocket.receive_bytes(), 10)
            # except TimeoutError:
            #     # close the connection to the transcriber as Deepgram timesout when 
            #     # it doesn't receive audio data for 10 seconds
            #     print("Disconnected Deepgram after 10 seconds of inactivity.")
            #     if send_ping_task:
            #         send_ping_task.cancel()
            #     if dg_connection:
            #         await transcriber.disconnect_deepgram(dg_connection)
            #         dg_connection = None
if __name__ == "__main__":
    ip_address = get_eth0_ip()
    if ip_address:
        print(f"Server is running at ws://{ip_address}:8999/communicate")
    else:
        print("Failed to retrieve IP address.")
    
    import uvicorn
    uvicorn.run(app, host=ip_address, port=8999)
