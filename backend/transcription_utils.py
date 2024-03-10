import transcriber
from llm import TranscriptionFormatter, ChatModel, ModelResponseHandler, ShouldRespondDecider
from reactivex import Subject
from typing import List
from websockets import ConnectionClosed
from deepgram import AsyncLiveClient
import asyncio
import aiortc
import av

## CONSTANTS
MIN_WORD_COUNT = 16
MAX_CONCURRENT_TASKS = 10

async def handle_transcriptions(transcription_queue: asyncio.Queue):
    transcription_formatter = TranscriptionFormatter()
    should_respond_decider = ShouldRespondDecider()
    chat_model = ChatModel()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    while True:
        async with semaphore:
            transcription = await transcription_queue.get()

            formatted_transcription = await transcription_formatter.run(transcription)
            model_should_respond = await should_respond_decider.run(formatted_transcription)
            print("Should respond: {}".format(model_should_respond))
            if model_should_respond is False:
                continue

            transcription_formatter.clear_history()

            model_response = []
            count = 0
            async for token in chat_model.run(formatted_transcription):
                model_response.append(token)
                count += 1

                if count == 5:
                    response_str = "".join(model_response)
                    print(response_str)
                    model_response = []
                    count = 0

            # Check if there are any remaining tokens
            if model_response:
                response_str = "".join(model_response)
                print(response_str)

        
                
async def handle_audio_stream(track: aiortc.MediaStreamTrack, closed_connection_event: asyncio.Event):
    print("Event: {}".format(closed_connection_event))
    ## State
    deepgram_conn = None
    transcription_observable: Subject = Subject()
    send_ping_task: asyncio.Task = None

    transcription_processing_queue = asyncio.Queue()

    handle_transcription_task = asyncio.create_task(handle_transcriptions(transcription_processing_queue))

    transcription_observable.subscribe(
        on_next=lambda transcription: transcription_processing_queue.put_nowait(transcription)
    )

    try:
        while closed_connection_event.is_set() == False:
            frame: av.AudioFrame = await track.recv()
            # print("Received audio frame")
            audio_data = frame.to_ndarray()[0]
            data = audio_data.tobytes()

            if not deepgram_conn:
                # logging.debug("Creating a connection to deepgram server")
                deepgram_conn = await transcriber.connect_to_deepgram(transcription_observable)
                # logging.debug("Starting send_ping_task")
                # send_ping_task = asyncio.create_task(transcriber.send_ping(deepgram_conn))
            try:
                if deepgram_conn:
                    # print("Sending bytes to transcriber")
                    await transcriber.send_data_deepgram(data, deepgram_conn) 
            except Exception as e:
                print(f"Failed to send data: {e}") 
    except ConnectionClosed as conn_err:
        print("Deepgram connection has been closed!")
    except Exception as e:
        print("Received an exception: {}".format(e))    
    finally:
        if handle_transcription_task.cancelled == False:
            handle_transcription_task.cancel()

        if send_ping_task is not None and send_ping_task.cancelled == False:
            send_ping_task.cancel()

        if deepgram_conn is not None:
            await transcriber.disconnect_deepgram(deepgram_conn)
