from dotenv import load_dotenv
import os
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    AsyncLiveClient
)
import time
from typing import List
import json
import asyncio
load_dotenv()
API_KEY = os.getenv("DG_API_KEY")

# config = DeepgramClientOptions(
#     verbose=logging.DEBUG, options={"keepalive": "true"}
# )

# deepgram = DeepgramClient(API_KEY, config=config)

deepgram = DeepgramClient(API_KEY)

async def connect_to_deepgram(transcription_observable):
    options = LiveOptions(
        language="en-US",
        punctuate=True,
        filler_words=True,
        numerals=True,
        encoding="linear16",
        sample_rate=48000,
        endpointing=True
    )
    
    print("CONNECTING TO DEEPGRAM LIVE")
    dg_connection: AsyncLiveClient = deepgram.listen.asynclive.v("1")

    async def on_message(self, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if len(sentence) == 0:
            return
        
        print("{}".format(sentence))
        
    async def on_metadata(self, metadata, **kwargs):
        print(f"{metadata}")

    async def on_error(self, error, **kwargs):
        print(f"{error}")

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

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
        print("Sending Ping")
        await dg_connection.send(json.dumps({"type": "KeepAlive"}))
        await asyncio.sleep(3)
