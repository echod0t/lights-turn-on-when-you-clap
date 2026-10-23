import sounddevice as sd
import numpy as np
import time

print("Clap detector running...")
print("Press Ctrl+C to stop.")

last_clap_time = 0

while True:
    recording = sd.rec(1323, samplerate=44100, channels=1)
    sd.wait()

    samples = recording[:, 0]

    loudness = np.sqrt(np.mean(samples ** 2))

    spectrum = np.abs(np.fft.rfft(samples))
    frequencies = np.fft.rfftfreq(len(samples), 1 / 44100)

    total_energy = np.sum(spectrum ** 2)
    high_energy = np.sum(spectrum[frequencies > 2000] ** 2)

    if total_energy == 0:
        continue

    high_ratio = high_energy / total_energy

    current_time = time.time()

    if (
        loudness > 0.035
        and high_ratio > 0.20
        and current_time - last_clap_time > 0.5
    ):
        print("Loudness:", round(loudness, 3), "High:", round(high_ratio, 3))

        last_clap_time = current_time
