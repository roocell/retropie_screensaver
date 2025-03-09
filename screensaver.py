#!/usr/bin/env python3

import time
import subprocess
from evdev import InputDevice, list_devices, ecodes
import select

# Timeout settings
timeout = 60  # Total inactivity time before turning off the display
check_interval = 10  # How often to check for activity
max_attempts = timeout // check_interval  # Number of missed checks before turning off display

# Track missed activity checks
missed_attempts = 0
# Get current display state
result = subprocess.run(["vcgencmd", "display_power"], capture_output=True, text=True)
display_on = '1' in result.stdout  # Check if the display is ON

def reset_timer():
    """Resets the inactivity counter when a key or mouse event is detected."""
    global missed_attempts, display_on
    missed_attempts = 0
    if not display_on:
        print("Activity detected, turning display ON")
        subprocess.run(["vcgencmd", "display_power", "1"])
        display_on = True

# Find input devices
devices = [InputDevice(dev) for dev in list_devices()]
input_devices = [dev for dev in devices if dev.name != 'dummy']  # Filter out dummy devices

# Set up select for non-blocking reads
device_fds = [device.fd for device in input_devices]

# Start monitoring the input devices
print("Monitoring for user input...")
for device in input_devices:
    print(f"Monitoring device: {device.name}")

try:
    while True:
        # Use select to check for available events from the devices
        r, _, _ = select.select(device_fds, [], [], check_interval)

        # Process events if any
        for fd in r:
            device = next(dev for dev in input_devices if dev.fd == fd)
            for event in device.read():
                if event.type == ecodes.EV_KEY or event.type == ecodes.EV_REL:  # Key press or mouse movement
                    reset_timer()

        missed_attempts += 1
        print(f"No activity detected ({missed_attempts}/{max_attempts})")

        if missed_attempts >= max_attempts and display_on:
            print("Timeout reached, turning display OFF")
            subprocess.run(["vcgencmd", "display_power", "0"])
            display_on = False

except KeyboardInterrupt:
    print("Stopping input monitor.")

