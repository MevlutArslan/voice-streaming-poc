from langchain_core.prompts import (
    HumanMessagePromptTemplate, ChatPromptTemplate, PromptTemplate, FewShotPromptTemplate, MessagesPlaceholder
)
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import SystemMessage
from openai import AsyncOpenAI
# chat_client = AsyncOpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")
from typing import List, Dict
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.chains import LLMChain
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
            You are an AI in a large AI chain of operations that passively listens to the user thinking out loud. 
            As a Decision making layer, your job is to determine if the AI should respond to the user.

            Some of the conditions that require AI to intervene are:
            1. When the user asks specifically asks you a question.
            2. When the user has made a substantial error in their thinking.
            3. When the user is drifting away from the main topic and is getting distracted.

            Please return a JSON object as your response using the following key-value pair:
            "model_should_respond": <True or False>
            '''
        )
        
        human_message_prompt = HumanMessagePromptTemplate.from_template("{transcript}")
        
        prompt = ChatPromptTemplate.from_messages([system_message,human_message_prompt])

        chain = prompt | self.model | self.layer_two_output_parser
        result = await chain.ainvoke({"transcript":message})
        return result["model_should_respond"]
    
    async def run(self, transcript: str) -> tuple[bool, str]:
        layer_one_output = await self.format_transcription(transcript)
        layer_two_output = await self.detect_end_of_thought(layer_one_output)
        
        return (layer_two_output, layer_one_output)

class ChatModel:
    def __init__(self) -> None:
        self.model = ChatOpenAI(
            model="gpt-4",
            streaming=True,
            temperature=0.5
        )
        
        system_message = SystemMessage('''
        As an LLM used in a voice chat environment, prioritize brevity and focus in your responses. 
        Avoid lengthy or verbose answers unless absolutely necessary. Your goal is to provide concise and relevant information that is 
        easy to understand and digest in a conversational setting.
    
        Please ensure that your responses are tailored to the context of the conversation and address the user's query directly. 
        Avoid unnecessary details or extraneous information that may detract from the clarity and effectiveness of your response.

        Remember, in a voice chat environment, clear and succinct communication is key to maintaining engagement and facilitating 
        smooth interactions. Keep your answers brief and to the point, unless additional context or explanation is required to fully 
        address the user's inquiry.
        ''')
                                   
        human_message_prompt = HumanMessagePromptTemplate.from_template("{message}")
        
        prompt = ChatPromptTemplate.from_messages([
            system_message,
            MessagesPlaceholder(variable_name="history"), 
            human_message_prompt
        ])
       
        self.chat_history = {}
        
        self.chain = prompt | self.model

        self.chain_with_memory = RunnableWithMessageHistory(
            self.chain,
            self.get_session_history,
            input_messages_key="message",
            history_messages_key="history"
        )
        
    async def invoke(self, message: str):
        response_stream = self.chain_with_memory.astream({"message": message}, config={"configurable": {"session_id": "abc123"}})
        async for partial_response in response_stream:
            yield partial_response.content
                
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.chat_history:
            self.chat_history[session_id] = ChatMessageHistory()
        return self.chat_history[session_id]
            
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
            Try not to end the result_text with the following structure "1." where the output parser might have trouble. 
            
            If you have deemed should_return_response to be True then return a JSON object with key-value mappings using:
            "should_return_response": <True or False>
            "response_text": String
            
            If you have deemed should_return_response to be False then return only a JSON with "should_return_response": <True or False>
        ''')
        human_message_prompt = HumanMessagePromptTemplate.from_template("{model_response}")

        prompt = ChatPromptTemplate.from_messages([system_message, human_message_prompt])
        
        chain: LLMChain = prompt | self.model | self.output_parser
        
        result = await chain.ainvoke({"model_response": model_response})
        should_return_response = result["should_return_response"]
        
        if should_return_response:
            return (should_return_response, result["response_text"])
        
        return (should_return_response, "")
        
        