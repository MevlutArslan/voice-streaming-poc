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