import wave
import numpy as np


def analyse_file(filename):
    with wave.open(filename, "rb") as file:
        frames = file.readframes(file.getnframes())
        sample_rate = file.getframerate()

    samples = np.frombuffer(frames, dtype=np.int16).astype(float) / 32768

    chunk_size = 1323  # 30 ms
    results = []

    for start in range(0, len(samples) - chunk_size, chunk_size):
        chunk = samples[start:start + chunk_size]

        loudness = np.sqrt(np.mean(chunk ** 2))

        spectrum = np.abs(np.fft.rfft(chunk))
        frequencies = np.fft.rfftfreq(len(chunk), 1 / sample_rate)

        total_energy = np.sum(spectrum ** 2)
        high_energy = np.sum(spectrum[frequencies > 2000] ** 2)

        if total_energy == 0:
            continue

        high_ratio = high_energy / total_energy

        results.append((loudness, high_ratio))

    results.sort(reverse=True)

    print("\n", filename)
    print("----------------")

    for loudness, high_ratio in results[:5]:
        print(
            "Loudness:",
            round(loudness, 3),
            "High:",
            round(high_ratio, 3)
        )


analyse_file("clap.wav")
analyse_file("shout.wav")
analyse_file("box.wav")