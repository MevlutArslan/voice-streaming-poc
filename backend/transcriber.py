from dotenv import load_dotenv
import os
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    LiveClient
)
import asyncio
import time

load_dotenv()
API_KEY = os.getenv("DG_API_KEY")

# config = DeepgramClientOptions(
#     verbose=logging.DEBUG, options={"keepalive": "true"}
# )

# deepgram = DeepgramClient(API_KEY, config=config)

deepgram = DeepgramClient(API_KEY)

def connect_to_deepgram():
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
    dg_connection = deepgram.listen.live.v("1")

    def on_message(self, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if len(sentence) == 0:
            return
        print(f"Received message: {sentence}")
        
    def on_metadata(self, metadata, **kwargs):
        print(f"{metadata}")

    def on_error(self, error, **kwargs):
        print(f"{error}")

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    dg_connection.start(options)

    return dg_connection

def disconnect_deepgram(dg_connection):
    if dg_connection:
        print("DISCONNECTING FROM DEEPGRAM")
        dg_connection.finish()

def send_data_deepgram(data, dg_connection):
    if dg_connection:
        dg_connection.send(data)

def send_ping(dg_connection: LiveClient, socketClosed):
    while True:
        if socketClosed:
            print("Detected Socket Closure, Exiting Send_Ping loop")
            break
        print("Sending Ping")
        dg_connection.send_ping()
        time.sleep(3)
