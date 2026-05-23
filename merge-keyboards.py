#!/usr/bin/env python3
import asyncio
import evdev
from evdev import UInput, ecodes

KEYBOARDS = [
    # Desktop
    "/dev/input/by-path/pci-0000:00:14.0-usb-0:2.3:1.0-event-kbd",
    "/dev/input/by-path/pci-0000:00:14.0-usb-0:2.4:1.0-event-kbd",
    # Laptop
    "/dev/input/by-path/pci-0000:00:14.0-usb-0:4:1.0-event-kbd",
    "/dev/input/by-path/pci-0000:00:14.0-usb-0:1:1.0-event-kbd",
]

async def handle(device, ui):
    async for event in device.async_read_loop():
        ui.write(event.type, event.code, event.value)
        ui.syn()

async def main():
    devices = []
    for path in KEYBOARDS:
        try:
            dev = evdev.InputDevice(path)
            dev.grab()
            devices.append(dev)
        except Exception as e:
            print(f"Skipping {path}: {e}")

    all_keys = set()
    for dev in devices:
        all_keys.update(dev.capabilities().get(ecodes.EV_KEY, []))

    ui = UInput({ecodes.EV_KEY: list(all_keys)}, name="merged-keyboard")

    await asyncio.gather(*[asyncio.create_task(handle(dev, ui)) for dev in devices])

asyncio.run(main())
