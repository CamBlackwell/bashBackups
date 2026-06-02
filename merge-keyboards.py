#!/usr/bin/env python3
import asyncio
import evdev
from evdev import UInput, ecodes

KEYBOARDS = [
    "/dev/input/by-path/pci-0000:00:14.0-usb-0:2.3:1.0-event-kbd",
    "/dev/input/by-path/pci-0000:00:14.0-usb-0:2.4:1.0-event-kbd",
    "/dev/input/by-path/pci-0000:00:14.0-usb-0:4:1.0-event-kbd",
    "/dev/input/by-path/pci-0000:00:14.0-usb-0:1:1.0-event-kbd",
    "/dev/input/by-path/platform-i8042-serio-0-event-kbd",
    "/dev/input/by-id/usb-Dell_Computer_Corp_Dell_Keyboard_KB525C-event-kbd",
]

async def handle(device, ui, merged_state):
    async for event in device.async_read_loop():
        if event.type == ecodes.EV_KEY:
            old_count = merged_state.get(event.code, 0)
            if event.value == 1:
                merged_state[event.code] = old_count + 1
                if old_count == 0:
                    ui.write(event.type, event.code, event.value)
                    ui.syn()
            elif event.value == 0:
                new_count = old_count - 1
                if new_count <= 0:
                    merged_state[event.code] = 0
                    ui.write(event.type, event.code, event.value)
                    ui.syn()
                else:
                    merged_state[event.code] = new_count
            else:
                if old_count > 0:
                    ui.write(event.type, event.code, event.value)
                    ui.syn()
        else:
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

    if not devices:
        print("No keyboard devices found, exiting")
        return

    all_keys = set()
    for dev in devices:
        all_keys.update(dev.capabilities().get(ecodes.EV_KEY, []))

    ui = UInput({ecodes.EV_KEY: list(all_keys)}, name="merged-keyboard")
    merged_state = {}

    await asyncio.gather(*[asyncio.create_task(handle(dev, ui, merged_state)) for dev in devices])

asyncio.run(main())
