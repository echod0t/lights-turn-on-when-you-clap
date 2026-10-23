import wave
import numpy as np
import os


def analyse_file(filename):
    with wave.open(filename, "rb") as file:
        frames = file.readframes(file.getnframes())
        sample_rate = file.getframerate()

    samples = np.frombuffer(
        frames,
        dtype=np.int16
    ).astype(float) / 32768

    # 5 ms window, 2.5 ms step
    chunk_size = int(sample_rate * 0.005)
    step_size = int(sample_rate * 0.0025)

    rms_values = []
    centroids = []
    times = []

    for start in range(
        0,
        len(samples) - chunk_size,
        step_size
    ):
        chunk = samples[start:start + chunk_size]

        rms = np.sqrt(np.mean(chunk ** 2))

        windowed = chunk * np.hanning(len(chunk))
        spectrum = np.abs(np.fft.rfft(windowed))
        frequencies = np.fft.rfftfreq(
            len(chunk),
            1 / sample_rate
        )

        energy = spectrum ** 2
        total_energy = np.sum(energy)

        if total_energy == 0:
            continue

        centroid = np.sum(
            frequencies * energy
        ) / total_energy

        rms_values.append(rms)
        centroids.append(centroid)
        times.append(start / sample_rate)

    rms_values = np.array(rms_values)
    centroids = np.array(centroids)
    times = np.array(times)

    peak_index = np.argmax(rms_values)
    peak_rms = rms_values[peak_index]
    peak_centroid = centroids[peak_index]

    ten_percent = peak_rms * 0.10
    ninety_percent = peak_rms * 0.90

    low_index = None
    high_index = None

    for i in range(peak_index, -1, -1):
        if low_index is None and rms_values[i] <= ten_percent:
            low_index = i

        if high_index is None and rms_values[i] >= ninety_percent:
            high_index = i

        if low_index is not None and high_index is not None:
            break

    if low_index is not None and high_index is not None:
        attack_time = (
            times[high_index] - times[low_index]
        ) * 1000
    else:
        attack_time = None

    print()
    print(filename)
    print("----------------")
    print("Peak loudness:", round(peak_rms, 3))
    print("Peak spectral centroid:", round(peak_centroid, 0), "Hz")

    if attack_time is not None:
        print(
            "10-90% attack time:",
            round(attack_time, 1),
            "ms"
        )

    if (
        attack_time is not None
        and attack_time < 10
        and peak_centroid > 1200
    ):
        print("RESULT: CLAP")
    else:
        print("RESULT: NOT CLAP")


analyse_file("clap.wav")
analyse_file("shout.wav")
analyse_file("box.wav")