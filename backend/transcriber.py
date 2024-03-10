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

deepgram = DeepgramClient(API_KEY)

async def connect_to_deepgram(transcription_observable: Subject):
    options = LiveOptions(
        model="nova-2-conversationalai",
        language="en-US",
        punctuate=True,
        filler_words=True,
        numerals=True,
        encoding="linear16",
        sample_rate=48000,
        channels=2,
        endpointing=1500
        # interim_results=True,
        # utterance_end_ms=2000 # if silence of 2000ms/2 seconds is detected then feed into llm
    )
    
    print("Connecting to deepgram")
    dg_connection: AsyncLiveClient = deepgram.listen.asynclive.v("1")

    async def on_message(self, result: LiveResultResponse, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if len(sentence) == 0:
            return
        if result.is_final:
            print(sentence)
            transcription_observable.on_next(sentence)
    
    async def on_metadata(self, metadata, **kwargs):
        print(f"{metadata}")

    async def on_error(self, error, **kwargs):
        print(f"{error}")
        
    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    await dg_connection.start(options)

    return dg_connection

async def disconnect_deepgram(dg_connection: AsyncLiveClient):
    if dg_connection:
        print("Disconnecting from deepgram")
        await dg_connection.finish()

async def send_data_deepgram(data, dg_connection: AsyncLiveClient):
    if dg_connection:
        await dg_connection.send(data)

async def send_ping(dg_connection: AsyncLiveClient):
    while True:
        # print("Sending Ping")
        await dg_connection.send(json.dumps({"type": "KeepAlive"}))
        await asyncio.sleep(3)
