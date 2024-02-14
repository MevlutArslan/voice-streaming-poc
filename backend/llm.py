from openai import OpenAI
import pyttsx3
from pydub import AudioSegment
from pydub.playback import play
from io import BytesIO
from openai import AsyncOpenAI
# Point to the local server
from string import punctuation

# chat_client = AsyncOpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
chat_client = AsyncOpenAI()
async def message_llm(message: str):
    print("Received message request: {}".format(message))
    completion = await chat_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": '''You are the first in line in a complex voice-to-text processing pipeline. Your task is to fix typos, improve punctuation, and remove duplications in the message you receive, without making any other changes. Please format your output as {formatted: your_answer}.'''},
            {"role": "user", "content": f"message_to_format: {message}"},
            {"role": "system", "content": "Now you are a conversational model that answers to a user, reply to the formatted prompt."}
        ],
        temperature=0.3,
        stream=True
    )

    response = ""
    end_of_line_punctuation = {'.', '!', '?'}
    async for token in completion:
        content = token.choices[0].delta.content
        if content:
            last_char = content.strip()[-1] if content.strip() else None
            response += content
            if last_char in end_of_line_punctuation:
                print(response)
                response = ""
