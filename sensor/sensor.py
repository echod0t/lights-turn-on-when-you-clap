import sounddevice as sd
import numpy as np
import time
import queue


SAMPLE_RATE = 44100

WINDOW_SIZE = int(SAMPLE_RATE * 0.005)
HISTORY_SIZE = 40

MIN_LOUDNESS = 0.06
MIN_CENTROID = 700
MAX_ATTACK_MS = 20

MIN_SURGE_RATIO = 2.5

QUIET_LEVEL = 0.03
QUIET_WINDOWS_NEEDED = 20

COOLDOWN = 0.5


def calculate_features(samples):
    rms = np.sqrt(
        np.mean(samples ** 2)
    )

    windowed = samples * np.hanning(
        len(samples)
    )

    spectrum = np.abs(
        np.fft.rfft(windowed)
    )

    frequencies = np.fft.rfftfreq(
        len(samples),
        1 / SAMPLE_RATE
    )

    energy = spectrum ** 2
    total_energy = np.sum(energy)

    if total_energy == 0:
        return rms, 0

    centroid = np.sum(
        frequencies * energy
    ) / total_energy

    return rms, centroid


def detect_clap():
    audio_queue = queue.Queue(maxsize=20)

    rms_history = []
    centroid_history = []

    armed = True
    quiet_windows = 0

    def audio_callback(indata, frames, time_info, status):
        try:
            audio_queue.put_nowait(
                indata[:, 0].copy()
            )
        except queue.Full:
            pass

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=WINDOW_SIZE,
        callback=audio_callback
    ):

        while True:

            samples = audio_queue.get()

            rms, centroid = calculate_features(
                samples
            )

            rms_history.append(rms)
            centroid_history.append(centroid)

            if len(rms_history) > HISTORY_SIZE:
                rms_history.pop(0)
                centroid_history.pop(0)

            # Wait for the previous sound to finish
            if not armed:

                if rms < QUIET_LEVEL:
                    quiet_windows += 1
                else:
                    quiet_windows = 0

                if quiet_windows >= QUIET_WINDOWS_NEEDED:
                    armed = True
                    quiet_windows = 0

                continue

            if len(rms_history) < 10:
                continue

            # Find the loudest recent section
            recent_rms = np.array(
                rms_history[-3:]
            )

            peak_offset = np.argmax(
                recent_rms
            )

            peak_index = (
                len(rms_history)
                - 3
                + peak_offset
            )

            peak_rms = rms_history[
                peak_index
            ]

            peak_centroid = centroid_history[
                peak_index
            ]

            if peak_rms < MIN_LOUDNESS:
                continue

            # Compare the peak to the sound just before it
            baseline_start = max(
                0,
                peak_index - 8
            )

            baseline_values = rms_history[
                baseline_start:peak_index
            ]

            if len(baseline_values) == 0:
                continue

            baseline = np.mean(
                baseline_values
            )

            surge_ratio = peak_rms / (
                baseline + 0.005
            )

            if surge_ratio < MIN_SURGE_RATIO:
                continue

            # Measure how quickly the sound rose
            high_threshold = peak_rms * 0.80
            low_threshold = peak_rms * 0.30

            high_index = None

            for i in range(
                peak_index,
                -1,
                -1
            ):
                if rms_history[i] >= high_threshold:
                    high_index = i
                    break

            if high_index is None:
                continue

            low_index = None

            for i in range(
                high_index,
                -1,
                -1
            ):
                if rms_history[i] <= low_threshold:
                    low_index = i
                    break

            if low_index is None:
                continue

            attack_time = (
                high_index - low_index
            ) * 5

            # Final clap decision
            if (
                attack_time <= MAX_ATTACK_MS
                and peak_centroid >= MIN_CENTROID
            ):

                armed = False
                quiet_windows = 0

                return True


def main_test():
    print("Clap detector running...")
    print("Press Ctrl+C to stop.")

    while True:
        if detect_clap():
            print("CLAP DETECTED!")


if __name__ == "__main__":
    main_test()
