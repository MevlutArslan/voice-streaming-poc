from dotenv import load_dotenv
import os
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    AsyncLiveClient,
    LiveResultResponse
)
import time
from typing import List
import json
import asyncio
from reactivex import Subject

load_dotenv()
API_KEY = os.getenv("DG_API_KEY")

# config = DeepgramClientOptions(
#     verbose=logging.DEBUG, options={"keepalive": "true"}
# )

# deepgram = DeepgramClient(API_KEY, config=config)

deepgram = DeepgramClient(API_KEY)

async def connect_to_deepgram(transcriptions: List[str], transcription_observable: Subject):
    options = LiveOptions(
        model="nova-2-phonecall",
        language="en-US",
        punctuate=True,
        filler_words=True,
        numerals=True,
        encoding="linear16",
        sample_rate=48000,
        endpointing=True,
        # interim_results=True,
        # utterance_end_ms=2000 # if silence of 2000ms/2 seconds is detected then feed into llm
    )
    
    print("CONNECTING TO DEEPGRAM LIVE")
    dg_connection: AsyncLiveClient = deepgram.listen.asynclive.v("1")

    async def on_message(self, result: LiveResultResponse, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if len(sentence) == 0:
            return
        if result.is_final:
            transcriptions.append(sentence)
            if len(transcriptions) > 1:
                concatenated_transcription = " ".join(transcriptions)
            else:
                concatenated_transcription = "".join(transcriptions)
            transcription_observable.on_next(concatenated_transcription)
    
    async def on_metadata(self, metadata, **kwargs):
        print(f"{metadata}")

    async def on_error(self, error, **kwargs):
        print(f"{error}")
        
    async def on_utterance_end(self, utterance_end, **kwargs):
        print("Finished Speaking")
        # full_transcription = " ".join(transcriptions)
        # transcription_observable.on_next(full_transcription)
        # transcriptions.clear()

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)
    # dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)

    await dg_connection.start(options)

    return dg_connection

async def disconnect_deepgram(dg_connection):
    if dg_connection:
        print("DISCONNECTING FROM DEEPGRAM")
        await dg_connection.finish()

async def send_data_deepgram(data, dg_connection: AsyncLiveClient):
    if dg_connection:
        await dg_connection.send(data)

async def send_ping(dg_connection: AsyncLiveClient):
    while True:
        # print("Sending Ping")
        await dg_connection.send(json.dumps({"type": "KeepAlive"}))
        await asyncio.sleep(3)
