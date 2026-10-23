import sounddevice as sd
import numpy as np
import wave

print("Recording will start in 3 seconds...")
sd.sleep(3000)

print("HIT THE BOX NOW!")

recording = sd.rec(
    5 * 44100,
    samplerate=44100,
    channels=1
)

sd.wait()

recording = (recording * 32767).astype(np.int16)

with wave.open("box.wav", "wb") as file:
    file.setnchannels(1)
    file.setsampwidth(2)
    file.setframerate(44100)
    file.writeframes(recording.tobytes())

print("Saved as box.wav")