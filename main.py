import asyncio
import time

from sensor.sensor import detect_clap
from bulb import start as start_zigbee, find_bulb, set_colour


CLAP_WINDOW = 1


async def turn_light_on(ep):
    print("Turning white light on...")

    await ep.on_off.on()

    # Set brightness to 200 out of 254
    await ep.level.move_to_level_with_on_off(200, 0)

    # Set neutral white with no requested fade
    await set_colour(ep, 0.3127, 0.3290, tenths=0)

    print("LIGHT ON")


async def turn_light_off(ep):
    print("Turning light off...")

    await ep.on_off.off()

    print("LIGHT OFF")


async def main():
    print("Connecting to Zigbee dongle...")

    app = await start_zigbee()

    try:
        ep = find_bulb(app)

        if ep is None:
            print("No bulb found.")
            print("Check your Zigbee connection.")
            return

        print("Bulb connected!")
        print("Clap twice to toggle the light on or off.")
        print("Press Ctrl+C to stop.")

        light_on = False
        clap_count = 0
        last_clap_time = 0.0

        while True:
            if await asyncio.to_thread(detect_clap):
                current_time = time.monotonic()

                if current_time - last_clap_time > CLAP_WINDOW:
                    clap_count = 0

                clap_count += 1
                last_clap_time = current_time

                print("Clap count:", clap_count)

                if clap_count == 2:
                    if light_on:
                        await turn_light_off(ep)
                        light_on = False
                    else:
                        await turn_light_on(ep)
                        light_on = True

                    clap_count = 0

            await asyncio.sleep(0.01)

    finally:
        print("Disconnecting from Zigbee...")
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nLights program stopped.")
