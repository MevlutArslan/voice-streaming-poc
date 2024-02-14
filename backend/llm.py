from openai import OpenAI
import pyttsx3
from pydub import AudioSegment
from pydub.playback import play
from io import BytesIO

# Point to the local server
chat_client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
tts_client = OpenAI()

def message_llm(message: str):
    completion = chat_client.chat.completions.create(
        model="local-model",
        messages=[
            {"role": "system", "content": "You are my experimental chatbot"},
            {"role": "user", "content": f"{message}"}
        ],
        temperature=0.5,
        stream=True
    )

    sentence = ""
    for token in completion:
        content = token.choices[0].delta.content
        if content:
            sentence += content
            # Check for punctuation marks to play the accumulated content
            if content.endswith(('.', '!', '?')):
                response = tts_client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    # response_format="opus",
                    input=sentence
                )

                for chunk in response.iter_bytes():
                    yield chunk
                
                sentence = ""

message_llm("hi, can you tell me about quantum mechanics and Einsteins view on it? Keep it concise.")
