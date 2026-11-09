import asyncio
import time
import pygame

from sensor.sensor import detect_clap, close_detector, DoubleClap
from bulb import start as start_zigbee, find_bulb, set_colour


CLAP_WINDOW = 0.8

SONG_FILE = "song.mp3"


async def turn_light_on(ep):
    print("Turning white light on...")

    await ep.on_off.on()

    await ep.level.move_to_level_with_on_off(254, 0)

    await set_colour(ep, 0.3127, 0.3290, tenths=0)

    if SONG_FILE:
        pygame.mixer.music.play()
        print("Playing music")

    print("LIGHT ON")


async def turn_light_off(ep):
    print("Turning light off")

    start_time = time.monotonic()

    if SONG_FILE:
        pygame.mixer.music.stop()
        print("Music stopped.")

    await ep.on_off.off()

    print("LIGHT OFF")


async def main():
    print("Connecting to Zigbee dongle")

    music_ready = False

    try:
        if SONG_FILE:
            pygame.mixer.init()
            pygame.mixer.music.load(SONG_FILE)
            music_ready = True
            print("Music loaded successfully.")
        else:
            print("No song selected yet.")

        app = await start_zigbee()

        try:
            ep = find_bulb(app)

            if ep is None:
                print("No bulb found.")
                print("Check your Zigbee connection")
                return

            print("Bulb connected")
            print("Clap twice to toggle the light on or off.")

            light_on = False
            gestures = DoubleClap()

            while True:
                clap_time = await asyncio.to_thread(detect_clap)
                if clap_time is not None:
                    print("Clap detected")
                    if gestures.add(clap_time):
                        if light_on:
                            await turn_light_off(ep)
                            light_on = False
                        else:
                            await turn_light_on(ep)
                            light_on = True

                await asyncio.sleep(0.01)

        finally:
            close_detector()
            print("Disconnecting from Zigbee")
            await app.shutdown()

    finally:
        if pygame.mixer.get_init():
            pygame.mixer.quit()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nLights program stopped.")
