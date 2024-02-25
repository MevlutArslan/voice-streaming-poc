from langchain_core.prompts import HumanMessagePromptTemplate, ChatPromptTemplate, PromptTemplate, FewShotPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import SystemMessage
from openai import AsyncOpenAI
# chat_client = AsyncOpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
from typing import List
class TranscriptionHandler:
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4", temperature=0)
        self.layer_one_output_parser = StrOutputParser()
        self.layer_two_output_parser = JsonOutputParser()
        
    async def format_transcription(self, transcription: str) -> str:
        system_message = SystemMessage('''
            You are a language formatter tasked with refining the output 
            of a speech transcription engine. Your objective is to take 
            a series of unformatted words and sentences and organize 
            them into coherent, grammatically correct passages with 
            appropriate punctuation, without altering the original 
            content of the text. If the sentence is incomplete leave it as incomplete and return the corrected string in whatever state it may be in.
            
            Example: "Well, I'm trying to figure out how to what you might call it, how to prompt my model properly.  Do do you think using multiple layers of elements Could  Do you think using multi  layers of LLMs  be useful?"
            Formatted: "Well... I am trying to figure out how to... what you might call it... how to prompt my model properly. Do you think using multiple layers of LLMs be useful?
            
            Only respond with the updated transcript and nothing else.
            ''')
        
        human_message_prompt = HumanMessagePromptTemplate.from_template("{transcript}")
        
        prompt = ChatPromptTemplate.from_messages([system_message,human_message_prompt])
        
        chain = prompt | self.model | self.layer_one_output_parser
        
        return await chain.ainvoke({"transcript": transcription})
    
    async def detect_end_of_thought(self, message: str) -> bool:
        system_message = SystemMessage(
           '''
            You are tasked with developing an end-of-thought detection system that accurately identifies pauses or shifts 
            in conversation indicating the completion of a user's current idea. Your objective is to analyze incoming speech 
            data and determine whether the user's current train of thought has concluded or if further input is required.

            Consider various linguistic cues and patterns that signify the end of a thought, such as concluding statements, 
            pauses, or shifts in topic. Additionally, take into account the context and coherence of the conversation to 
            accurately gauge the user's intended message.

            Upon detecting an apparent end of thought, your system should provide a signal indicating readiness to proceed with 
            further interaction or action. Conversely, if the analysis suggests that the user's thought is still ongoing, withhold 
            the signal to allow for continued listening and processing.

            Your role is crucial in facilitating smooth and efficient communication between the user and the system, ensuring 
            timely responses and appropriate handling of input.

            Your output format should adhere to the following structure of a JSON object:
            {
                "end_of_thought_detected": <boolean> (True or False)
            }
            '''
        )
        
        human_message_prompt = HumanMessagePromptTemplate.from_template("{transcript}")
        
        prompt = ChatPromptTemplate.from_messages([system_message,human_message_prompt])

        chain = prompt | self.model | self.layer_two_output_parser
        result = await chain.ainvoke({"transcript":message})
        return result["end_of_thought_detected"]
    
    async def run(self, transcript: str) -> tuple[bool, str]:
        layer_one_output = await self.format_transcription(transcript)
        layer_two_output = await self.detect_end_of_thought(layer_one_output)
        
        return (layer_two_output, layer_one_output)


async def generate_response(client: AsyncOpenAI, prompt: str):
    async with await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are an LLM used in a voice chat environment, make sure you do not respond with things like: 'Here is a python script ...'"},
                  {"role": "user", "content": prompt}],
        stream=True,
        temperature=0.5
    ) as response_stream:
        async for partial_response in response_stream:
            yield partial_response.choices[0].delta.content
            
            
class ModelResponseHandler:
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4", temperature=0)
        self.output_parser = JsonOutputParser()
    
    async def run(self, model_response: List[str]) -> tuple[bool, str]:
        # print("Received a ModelResponseHandler.Run request for the tokens: {}".format(model_response))
        system_message = SystemMessage('''
            You have been assigned the task of assembling a stream of tokens generated by a Large Language Model (LLM) asynchronously. 
            Your objective is to stich together these tokens to allow for it to be an input into a Text-to-Speech (TTS) model.

            Your task involves monitoring the incoming stream of tokens and determining when you have accumulated enough tokens to form a complete sentence suitable for TTS input. 
            Once you have identified such a sentence, your system should return True along with the stitched-together tokens.

            Remove explicit displays of tokens like escape characters.
            Make sure to format the string to accomodate an output parser to be able to extract your response as a JSON object.
            
            please structure your output as a valid Json object using the following variable names: response_text for the string, should_return_response for the Boolean 
        ''')
        human_message_prompt = HumanMessagePromptTemplate.from_template("{model_response}")

        prompt = ChatPromptTemplate.from_messages([system_message, human_message_prompt])
        
        chain = prompt | self.model | self.output_parser
        
        result = await chain.ainvoke({"model_response": model_response})
        
        return (result["should_return_response"], result["response_text"])
        
        