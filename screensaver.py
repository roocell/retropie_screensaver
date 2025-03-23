#!/usr/bin/env python3

import time
import subprocess
from evdev import InputDevice, list_devices, ecodes
import select

import board
import neopixel


# neopixels
pixel_pin = board.D21
num_pixels = 34
ORDER = neopixel.GRB
pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.2, auto_write=False, pixel_order=ORDER
)

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b) if ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)

def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            pixel_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait)

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


rainbow_cycle(0.001)  # rainbow cycle with 1ms delay per step
pixels.fill((255, 255, 255))
pixels.show()


try:
    while True:
        # Use select to check for available events from the devices
        r, _, _ = select.select(device_fds, [], [], check_interval)

        # Process events if any
        for fd in r:
            device = next(dev for dev in input_devices if dev.fd == fd)
            for event in device.read():
                if event.type == ecodes.EV_KEY or event.type == ecodes.EV_REL or event.type == ecodes.EV_ABS:  # Key press or mouse movement
                    reset_timer()
                    rainbow_cycle(0.001)  # rainbow cycle with 1ms delay per step
                    pixels.fill((255, 255, 255))
                    pixels.show()

        missed_attempts += 1
        print(f"No activity detected ({missed_attempts}/{max_attempts})")

        if missed_attempts >= max_attempts and display_on:
            print("Timeout reached, turning display OFF")
            subprocess.run(["vcgencmd", "display_power", "0"])
            display_on = False
            pixels.fill((0, 0, 0))
            pixels.show()

except KeyboardInterrupt:
    print("Stopping input monitor.")

