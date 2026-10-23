import sounddevice as sd
import numpy as np
import time


SAMPLE_RATE = 44100
RECORD_SECONDS = 2
NUMBER_OF_CLAPS = 5


def analyse_sound(recording):
    samples = recording[:, 0]

    window_size = int(SAMPLE_RATE * 0.005)   # 5 ms
    step_size = int(SAMPLE_RATE * 0.0025)    # 2.5 ms

    loudness_values = []
    centroid_values = []
    times = []

    for start in range(
        0,
        len(samples) - window_size,
        step_size
    ):
        chunk = samples[start:start + window_size]

        rms = np.sqrt(np.mean(chunk ** 2))

        windowed = chunk * np.hanning(len(chunk))

        spectrum = np.abs(
            np.fft.rfft(windowed)
        )

        frequencies = np.fft.rfftfreq(
            len(chunk),
            1 / SAMPLE_RATE
        )

        energy = spectrum ** 2
        total_energy = np.sum(energy)

        if total_energy == 0:
            continue

        centroid = np.sum(
            frequencies * energy
        ) / total_energy

        loudness_values.append(rms)
        centroid_values.append(centroid)
        times.append(start / SAMPLE_RATE)

    loudness_values = np.array(loudness_values)
    centroid_values = np.array(centroid_values)
    times = np.array(times)

    peak_index = np.argmax(loudness_values)

    peak_loudness = loudness_values[peak_index]
    peak_centroid = centroid_values[peak_index]

    # Find the beginning of the loud attack
    ten_percent = peak_loudness * 0.10
    ninety_percent = peak_loudness * 0.90

    low_index = None
    high_index = None

    for i in range(peak_index, -1, -1):
        if low_index is None and loudness_values[i] <= ten_percent:
            low_index = i

        if high_index is None and loudness_values[i] >= ninety_percent:
            high_index = i

        if low_index is not None and high_index is not None:
            break

    if low_index is not None and high_index is not None:
        attack_time = (
            times[high_index] - times[low_index]
        ) * 1000
    else:
        attack_time = None

    return peak_loudness, peak_centroid, attack_time


print()
print("======================================")
print("        FRESH CLAP ANALYSIS")
print("======================================")
print()
print("We are collecting NEW clap samples.")
print("Nothing from clap.wav is being used.")
print()

time.sleep(2)

results = []

for number in range(1, NUMBER_OF_CLAPS + 1):

    print()
    print(f"CLAP {number}")
    print("Get ready...")
    time.sleep(2)

    print("CLAP NOW!")

    recording = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1
    )

    sd.wait()

    result = analyse_sound(recording)
    results.append(result)

    loudness, centroid, attack = result

    print()
    print("Loudness:", round(loudness, 3))
    print("Centroid:", round(centroid, 0), "Hz")

    if attack is not None:
        print("Attack:", round(attack, 1), "ms")
    else:
        print("Attack: not measured")


print()
print("======================================")
print("              RESULTS")
print("======================================")

for number, result in enumerate(results, start=1):

    loudness, centroid, attack = result

    print()
    print(
        f"Clap {number}:",
        f"Loudness={loudness:.3f},",
        f"Centroid={centroid:.0f} Hz,",
        f"Attack={attack:.1f} ms"
        if attack is not None
        else "Attack=unknown"
    )

print()
print("======================================")
print("          WHAT WE LEARNED")
print("======================================")

valid_results = [
    result
    for result in results
    if result[2] is not None
]

if valid_results:

    loudnesses = [result[0] for result in valid_results]
    centroids = [result[1] for result in valid_results]
    attacks = [result[2] for result in valid_results]

    print(
        "Average loudness:",
        round(np.mean(loudnesses), 3)
    )

    print(
        "Average centroid:",
        round(np.mean(centroids), 0),
        "Hz"
    )

    print(
        "Average attack:",
        round(np.mean(attacks), 1),
        "ms"
    )

print()
print("Test complete.")