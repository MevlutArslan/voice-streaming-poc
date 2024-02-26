from langchain_core.prompts import (
    HumanMessagePromptTemplate, ChatPromptTemplate, MessagesPlaceholder
)
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import SystemMessage
from typing import List
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.chains import LLMChain

class TranscriptionHandler:
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4", temperature=0)
        self.json_parser = JsonOutputParser()
        
    async def run(self, transcription: str) -> tuple[bool, str]:
        print("Received Format request: {}".format(transcription))
        ## TODO: Improve this further
        system_message = SystemMessage('''
             You are a language formatter and AI component within a larger AI system designed to passively listen to the user's spoken 
             thoughts. Your role is to refine the output of a speech transcription engine and decide whether the AI should 
             respond to the user based on specific conditions.

            Your objective is to take a series of unformatted words and sentences, organize them into coherent, grammatically correct 
            passages with appropriate punctuation, and determine if the AI should respond. If the sentence is incomplete, leave 
            it as incomplete and leave the corrected string in whatever state it may be in and then decide if the model_should_respond.

            Example: "Well, I'm trying to figure out how to what you might call it, how to prompt my model properly.  Do do you think using multiple layers of elements Could  Do you think using multi  layers of LLMs  be useful?"
            Formatted: "Well... I am trying to figure out how to... what you might call it... how to prompt my model properly. Do you think using multiple layers of LLMs be useful?

            Please provide a JSON response with the following key-value pairs:
            "formatted_transcript": <String>,
            "model_should_respond": <True or False>
        ''')
        
        human_message_prompt = HumanMessagePromptTemplate.from_template("{transcript}")
        
        prompt = ChatPromptTemplate.from_messages([system_message, human_message_prompt])
        
        chain = prompt | self.model | self.json_parser
        result = await chain.ainvoke({"transcript": transcription})

        return (result["model_should_respond"], result["formatted_transcript"])

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
        
        