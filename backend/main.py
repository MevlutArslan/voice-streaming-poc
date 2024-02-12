from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from connection_manager import ConnectionManager, get_eth0_ip
import asyncio
import transcriber
from audio import float32_to_linear16_bytes
from llm import message_llm
import threading

app = FastAPI()
manager = ConnectionManager()

@app.websocket("/communicate")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    accumulated_bytes = b''

    dg_connection = None
    send_ping_exit_event = threading.Event()
    send_ping_thread: threading.Thread = None
    
    transcription_queue = []
    transcription_queue_lock = threading.Lock()
    try:
        while True:
            data = await websocket.receive_bytes()
            
            if not dg_connection:
                dg_connection = transcriber.connect_to_deepgram(transcription_queue, transcription_queue_lock)
                # NOTE: Sending ping frames doesn't seem to prevent the timeout...
                #       Needs further testing
                # send_ping_thread = threading.Thread(target=lambda: transcriber.send_ping(dg_connection, send_ping_exit_event))
                # send_ping_thread.start()

            # Accumulate received data
            accumulated_bytes += data
            
            try:
                if dg_connection:
                    # NOTE: we only need this because the client sends float32 buffers, 
                    #       which will be changed on the client side to get rid of this
                    int16_audio = float32_to_linear16_bytes(accumulated_bytes)
                    
                    transcriber.send_data_deepgram(int16_audio, dg_connection)
                    with transcription_queue_lock:
                        if len(transcription_queue) > 0:
                            print(f"Received transcription: {transcription_queue.pop()}")
            except Exception as e:
                print(f"Failed to send data: {e}")

            # Reset accumulated bytes and length
            accumulated_bytes = b''
    except WebSocketDisconnect:
        # Clean up resources, stop the stream, and close it
        manager.disconnect(websocket)
        send_ping_exit_event.set()
        # send_ping_thread.join()
        if dg_connection:
            transcriber.disconnect_deepgram(dg_connection)
            dg_connection = None
    # finally:
    #     # Clean up resources, stop the stream, and close it
    #     manager.disconnect(websocket)
    #     send_ping_exit_event.set()
    #     send_ping_thread.join()
    #     if dg_connection:
    #         transcriber.disconnect_deepgram(dg_connection)
    #         dg_connection = None
            
        
if __name__ == "__main__":
    ip_address = get_eth0_ip()
    if ip_address:
        print(f"Server is running at ws://{ip_address}:8999/communicate")
    else:
        print("Failed to retrieve IP address.")
    
    import uvicorn
    uvicorn.run(app, host=ip_address, port=8999)
