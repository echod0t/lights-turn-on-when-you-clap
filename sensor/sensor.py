"""Continuous clap detection. Importing this module does not open the microphone."""
import json
from pathlib import Path
import queue
import time
from collections import deque

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100
WINDOW_SIZE = int(SAMPLE_RATE * 0.005)
WINDOW_SECONDS = WINDOW_SIZE / SAMPLE_RATE
MIN_LOUDNESS = 0.06
MIN_CENTROID = 450
MAX_CENTROID = 2000
MAX_ATTACK_MS = 20
MIN_SURGE_RATIO = 2.5
QUIET_LEVEL = 0.03
QUIET_WINDOWS_NEEDED = 12
MIN_CLAP_GAP = 0.12
CLAP_WINDOW = 0.8
TOGGLE_COOLDOWN = 0.7
MAX_EVENT_SECONDS = 0.15


def calculate_features(samples):
    rms = float(np.sqrt(np.mean(samples ** 2)))
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    frequencies = np.fft.rfftfreq(len(samples), 1 / SAMPLE_RATE)
    energy = spectrum ** 2
    total = np.sum(energy)
    centroid = float(np.sum(frequencies * energy) / total) if total else 0.0
    return rms, centroid


class ClapState:
    """Track a whole transient instead of deciding on its first 5 ms block."""
    def __init__(self):
        self.history = deque(maxlen=40)
        self.quiet = 0
        self.armed = False
        self.event = None
        self.last_loud = None
        self.onset = None
        self.before = []
        self.peak = 0.0

    def process(self, rms, centroid, timestamp):
        previous = list(self.history)
        self.history.append(rms)

        quiet_level = max(QUIET_LEVEL, self.peak * 0.30)
        self.quiet = self.quiet + 1 if rms < quiet_level else 0

        if self.armed and rms >= MIN_LOUDNESS and len(previous) >= 8:
            self.armed = False
            self.quiet = 0
            self.attack_energy = 0.0
            self.weighted_frequency = 0.0
            self.onset = timestamp
            self.before = previous[-8:]
            self.peak = 0.0
            self.event = None

        if not self.armed:
            if self.onset is not None and timestamp - self.onset <= 0.025:
                self.attack_energy += rms ** 2
                self.weighted_frequency += centroid * rms ** 2
                if rms > self.peak:
                    self.peak = rms
                    baseline = float(np.mean(self.before))
                    surge = rms / (baseline + 0.005)
                    low_distance = next((i for i, value in enumerate(
                        reversed(self.before), 1) if value <= rms * 0.30), None)
                    attack_ms = ((timestamp - self.onset) +
                                 low_distance * WINDOW_SECONDS) * 1000 if low_distance else float('inf')
                    if (surge >= MIN_SURGE_RATIO and attack_ms <= MAX_ATTACK_MS):
                        self.event = self.onset
            if rms >= max(QUIET_LEVEL, self.peak * 0.30):
                self.last_loud = timestamp
            if self.quiet >= QUIET_WINDOWS_NEEDED:
                event = self.event
                last_loud = self.last_loud
                self.event = None
                self.onset = None
                self.peak = 0.0
                self.armed = True
                if (event is not None and last_loud - event <= MAX_EVENT_SECONDS
                        and MIN_CENTROID <= self.weighted_frequency / self.attack_energy <= MAX_CENTROID):
                    return event
        return None


class DoubleClap:
    def __init__(self):
        self.first = None
        self.blocked_until = float('-inf')

    def add(self, timestamp):
        if timestamp < self.blocked_until:
            return False
        if self.first is None or timestamp - self.first > CLAP_WINDOW:
            self.first = timestamp
            return False
        if timestamp - self.first < MIN_CLAP_GAP:
            return False
        self.first = None
        self.blocked_until = timestamp + TOGGLE_COOLDOWN
        return True


class RoomClapFilter:
    """Compare the spectrum around an impact with examples from this microphone."""
    def __init__(self):
        profiles = json.loads(Path(__file__).with_name('room_sound_profiles.json').read_text())
        self.claps = np.array(profiles['claps'])
        self.noises = np.array(profiles['screwdriver'] + profiles['bottle'])
        self.blocks = deque(maxlen=64)
        self.state = ClapState()

    def reset(self):
        self.blocks.clear()
        self.state = ClapState()

    def process(self, samples, frame):
        self.blocks.append((frame, samples))
        event = self.state.process(*calculate_features(samples), frame / SAMPLE_RATE)
        if event is None:
            return None
        audio = np.concatenate([block for _, block in self.blocks])
        onset = round(event * SAMPLE_RATE) - self.blocks[0][0]
        if onset < WINDOW_SIZE or onset + 4 * WINDOW_SIZE > len(audio):
            return None
        peak = onset + np.argmax(np.abs(audio[onset:onset + 4 * WINDOW_SIZE]))
        segment = audio[peak - WINDOW_SIZE:peak + 2 * WINDOW_SIZE]
        if len(segment) != 3 * WINDOW_SIZE:
            return None
        energy = np.abs(np.fft.rfft(segment * np.hanning(len(segment)))) ** 2
        bands = np.add.reduceat(energy, [0, 5, 10, 18, 30, 48, 78, 120])
        if bands.sum() == 0:
            return None
        shape = np.sqrt(bands / bands.sum())
        clap_distance = np.linalg.norm(self.claps - shape, axis=1).min()
        noise_distance = np.linalg.norm(self.noises - shape, axis=1).min()
        return event if clap_distance < noise_distance else None


class ClapDetector:
    def __init__(self):
        self.audio = queue.Queue(maxsize=200)
        self.room_filter = RoomClapFilter()
        self.stream = None
        self.frame_index = 0
        self.expected_frame = None

    def _callback(self, indata, frames, time_info, status):
        frame = self.frame_index
        self.frame_index += frames
        item = (time.monotonic(), frame, indata[:, 0].copy(), bool(status))
        try:
            self.audio.put_nowait(item)
        except queue.Full:
            pass

    def wait(self, timeout=0.1):
        if self.stream is None:
            stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                    blocksize=WINDOW_SIZE, callback=self._callback)
            try:
                stream.start()
            except BaseException:
                stream.close()
                raise
            self.stream = stream
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                arrival, frame, samples, discontinuity = self.audio.get(
                    timeout=max(0.001, deadline - time.monotonic()))
            except queue.Empty:
                return None
            if time.monotonic() - arrival > 0.25:
                self.room_filter.reset()
                self.expected_frame = None
                continue
            if discontinuity or (self.expected_frame is not None and frame != self.expected_frame):
                self.room_filter.reset()
            self.expected_frame = frame + len(samples)
            event = self.room_filter.process(samples, frame)
            if event is not None:
                return event
        return None

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None


_detector = None


def detect_clap():
    """Return the clap onset's monotonic timestamp, or None after a short wait."""
    global _detector
    if _detector is None:
        _detector = ClapDetector()
    return _detector.wait()


def close_detector():
    global _detector
    if _detector is not None:
        _detector.close()
        _detector = None


def main_test():
    print('Clap detector running... Press Ctrl+C to stop.')
    try:
        while True:
            if detect_clap() is not None:
                print('CLAP DETECTED!')
    finally:
        close_detector()


if __name__ == '__main__':
    main_test()
