
import asyncio
import sys

import zigpy_znp.zigbee.application as znp

PORT = "COM3"
DB = "zigbee.db"


async def start():
    return await znp.ControllerApplication.new(
        config={
            "device": {"path": PORT},
            "database_path": DB,
        },
        auto_form=True,
        start_radio=True,
    )


def find_bulb(app):
    """Find a colour bulb with On/Off and Colour clusters."""
    for dev in app.devices.values():
        for ep_id, ep in dev.endpoints.items():
            if (
                ep_id != 0
                and 0x0006 in ep.in_clusters
                and 0x0300 in ep.in_clusters
            ):
                return ep
    return None


async def pair(app):
    print("Pairing open for 120 seconds.")
    print("Switch the bulb off and on when prompted.")

    await app.permit(120)

    for _ in range(120):
        await asyncio.sleep(1)

        ep = find_bulb(app)

        if ep is None:
            continue

        device = ep.device
        print("Bulb detected. Waiting for initialization...")

        task = getattr(device, "_initialize_task", None)

        if task is not None and not task.done():
            try:
                await asyncio.wait_for(
                    asyncio.shield(task),
                    timeout=90,
                )
            except asyncio.TimeoutError:
                print("Initialization timed out.")
                return
            except asyncio.CancelledError:
                print("Initialization was cancelled.")
                return
            except Exception as exc:
                print(f"Initialization failed: {exc!r}")
                return

        if device.is_initialized:
            print("Bulb fully initialized and saved.")
        else:
            print("Bulb detected, but initialization is incomplete.")

        return

    print("No bulb found. Check that it is powered on.")


def xy(x, y):
    """Convert colour coordinates to Zigbee values."""
    return int(x * 65535), int(y * 65535)


async def set_colour(ep, x, y, tenths=5):
    cx, cy = xy(x, y)
    await ep.light_color.move_to_color(cx, cy, tenths)


async def test(app):
    """Turn the bulb on in white and leave it on."""
    ep = find_bulb(app)

    if ep is None:
        print("No bulb saved yet. Run: python bulb.py pair")
        return

    print("Turning bulb on in white...")

    await ep.on_off.on()
    await ep.level.move_to_level_with_on_off(254, 5)

    # Neutral white, approximately 6500 K on a capable colour bulb.
    await set_colour(ep, 0.3127, 0.3290)

    print("Bulb is on in white.")


async def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "test"

    if mode not in ("pair", "test"):
        print("Usage: python bulb.py pair")
        print("   or: python bulb.py test")
        return

    app = await start()

    try:
        if mode == "pair":
            await pair(app)
        else:
            await test(app)
    finally:
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
