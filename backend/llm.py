from openai import OpenAI
import pyttsx3
from pydub import AudioSegment
from pydub.playback import play
from io import BytesIO
from openai import AsyncOpenAI
# Point to the local server
from string import punctuation
import asyncio
# chat_client = AsyncOpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

async def message_llm(client: AsyncOpenAI, message: str):
    print("Received message request: {}".format(message))
    completion = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": '''
                You are a real-time transcription filtering model tasked with discerning whether 
                the ongoing speech input from the user requires further accumulation before it 
                can be processed by a language model to generate a meaningful response. 
                Your responsibility is to carefully evaluate the entirety of the message and 
                determine if additional context is necessary to form a complete and actionable 
                prompt or if the provided input is coherent enough for further processing.

                To ensure accurate decision-making, consider factors such as the user's intention, 
                the flow of the conversation, and the completeness of the information provided. 
                You may need to balance between waiting for additional input and providing timely 
                responses to maintain a smooth interaction.

                This approach encourages the model to consider the entire message before making a 
                decision, allowing the user to complete their thought before processing begins. 

                Example 1:
                In the bustling city, the streets were alive with activity. 
                People rushed past each other, their faces hidden behind masks of concentration 
                or laughter. Cars honked impatiently as they navigated through the crowded 
                intersections, while the distant sound of construction echoed through the air. 
                Above, the sky stretched out endlessly, a vast expanse of blue interrupted only 
                by the occasional cloud drifting lazily by. In the midst of it all, I found myself 
                lost in thought, marveling at the chaos and energy of urban life. There was a 
                sense of urgency in the air, a feeling that time was slipping away even as we 
                hurried to keep pace with it. And yet, amidst the hustle and bustle, there was 
                also a strange kind of beauty, a rhythm to the chaos that somehow made it all 
                feel strangely comforting. As I walked along the sidewalk, I couldn't help but 
                smile at the sheer vitality of the city around me, 
                grateful to be a part of its ever-changing tapestry.
            
                Output 1:
                {
                    "ready_for_processing": <False>
                }
                
                As although the input is complete anything you might comment on adds no value to the context.
                
                Example 2:
                I have been thinking about how prompting works, please correct me if I got 
                it wrong but I think all prompting does is to set the model's context window 
                to some part of its training set.
                
                Output 2:
                {
                    "ready_for_processing": <True>
                }
                
                The user is asking for your input so it means that you can add value to the context.
                
                Example 3:
                So... I have been reading about Einstein
                
                Output 3:
                {
                    "ready_for_processing": <False>
                }
                
                The user indicates an activity they are doing but hasn't completed their full explanation for you to make sense of it.
                
                **Output Format:**

                * Use the following JSON format:

                ```json
                {
                    "ready_for_processing": <True or False>
                }
             '''},
            {"role": "user", "content": f"message_to_format: {message}"},
        ],
        temperature=0,
        stream=True
    )
    

    # response = ""
    # end_of_line_punctuation = {'.', '!', '?'}
    # async for token in completion:
    #     content = token.choices[0].delta.content
    #     if content:
    #         last_char = content.strip()[-1] if content.strip() else None
    #         response += content
    #         if last_char in end_of_line_punctuation:
    #             print(response)
    #             response = ""
    
    response = ""
    end_of_line_punctuation = {'.', '!', '?'}
    print("LOG: WAITING FOR RESULT")
    async for token in completion:
        content = token.choices[0].delta.content
        if content:
            response += content

    print(response)

# async def test_function():
#     # message = '''In the quiet countryside, time seemed to slow to a gentle crawl. The air was filled with the sweet scent of wildflowers, carried on a soft breeze that rustled through the trees. Sunlight filtered through the leaves, casting dappled patterns of light and shadow on the lush green grass below. Birds chirped melodiously in the distance, their songs blending harmoniously with the gentle babbling of a nearby brook. In this idyllic setting, there was no rush, no urgency. Instead, there was a profound sense of peace and serenity, as if the world had paused for a moment to catch its breath. Here, amidst the beauty of nature, I found solace and tranquility, grateful for the opportunity to simply be, and to savor the quiet beauty that surrounded me.'''
#     # message = "What are the differences between COmputer Sciece, Computer uhhh Computer Engineering and Software Engineeering?"
#     # message = "I have been thinking about how prompting works, please correct me if I got it wrong but I think all prompting does is to set the model's context window to some part of its training set."
#     message = "So... I have been hearing about this thing called diffusion models... what are they used for?"
#     await message_llm(message)

# # Call the test function
# asyncio.run(test_function())

from langchain_core.prompts import HumanMessagePromptTemplate, ChatPromptTemplate, PromptTemplate, FewShotPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import SystemMessage

class PreliminaryLLM:
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4", temperature=0)
        
    def feed_into_layer_one(self, transcription: str) -> str:
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
        
        output_parser = StrOutputParser()
        
        prompt = ChatPromptTemplate.from_messages([system_message,human_message_prompt])
        
        chain = prompt | self.model | output_parser
        
        return chain.invoke({"transcript": transcription})
    
    def feed_into_layer_two(self, message: str) -> bool:
        system_message = SystemMessage(
            '''
            You are an end-of-thought detector tasked with analyzing accumulated 
            transcripts to determine whether the user's current train of thought 
            has concluded or if further input is required. Your objective is to 
            process a series of transcript accumulations, each containing the user's 
            spoken thoughts, and assess whether the content indicates a natural 
            pause or completion of the user's current idea. Consider various 
            linguistic cues and patterns that signify the end of a thought, 
            such as concluding statements, pauses, or shifts in topic. 
            Additionally, take into account the context and coherence of the 
            accumulated transcripts to accurately gauge the user's intended message. 
            Upon detection of an apparent end of thought, provide a signal 
            indicating readiness to proceed with further interaction or action. 
            Conversely, if the analysis suggests that the user's thought is still 
            ongoing, withhold the signal to allow for continued listening and 
            processing. Your role is critical in facilitating smooth and 
            efficient communication between the user and the transcription system, 
            ensuring timely responses and appropriate handling of input.
            
            you should output in the following format and should not return anything else: 
            JSON: {
                "end_of_thought_detected": <boolean> (True or False)
            }
            '''
        )
        
        human_message_prompt = HumanMessagePromptTemplate.from_template("{transcript}")
        output_parser = JsonOutputParser()
        
        prompt = ChatPromptTemplate.from_messages([system_message,human_message_prompt])

        chain = prompt | self.model | output_parser
        
        return chain.invoke({"transcript":message})["end_of_thought_detected"]
    
    def run(self, transcript: str) -> str:
        layer_one_output = self.feed_into_layer_one(transcript)
        layer_two_output = self.feed_into_layer_two(layer_one_output)
        
        return layer_two_output
    