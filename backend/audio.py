import numpy as np

'''
https://pypi.org/project/SpeechRecognition/1.5.0/#:~:text=The%20actual%20energy%20threshold%20you,what%20values%20will%20work%20best.
'''
def is_audio_silent(data, threshold=1.0) -> bool:
    # Convert raw bytes to NumPy array (assuming 32-bit float audio samples)
    audio_samples = np.frombuffer(data, dtype=np.float32)

    # Calculate energy of the audio signal
    energy = np.sum(audio_samples ** 2)

    # Adjust the threshold based on your specific requirements
    if energy < threshold:
        print(f"Pause detected at energy level: {energy}")
        return True
        # Perform additional actions for pauses if needed
    else:
        print(f"Speech detected at energy level: {energy}")
        return False
        # Perform additional actions for speech if needed
    
from typing import List
import os
from io import BytesIO
from scipy.io.wavfile import write

def save_audio_as_file(data, file_path='audio.wav', rate=48000):
    try:
        # Use scipy.io.wavfile.write to save the NumPy array as a WAV file
        write(file_path, rate, data)
        return file_path  # Return the fixed file path if successful

    except Exception as e:
        print(f"Error saving audio file: {str(e)}")
        return None  # Return None in case of an error
    
def get_transcription(filepath: str) -> dict:
    import whisper

    # Load the pre-trained model
    model = whisper.load_model("small")

    # Transcribe the audio file
    transcription = model.transcribe(filepath)
    return transcription