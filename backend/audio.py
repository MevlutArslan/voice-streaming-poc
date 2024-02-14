import numpy as np

def float32_to_linear16_bytes(float32_bytes):
    # Decode bytes to float32 array
    float32_array = np.frombuffer(float32_bytes, dtype=np.float32)
    
    # Convert float32 array to linear16
    linear16_array = (float32_array * 32767).astype(np.int16)
    
    # Encode linear16 data to bytes
    # "order='C'" means that elements are stored in row-major order
    linear16_bytes = linear16_array.tobytes(order='C')
    
    return linear16_bytes