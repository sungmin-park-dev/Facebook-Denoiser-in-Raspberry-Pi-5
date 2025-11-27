#!/usr/bin/env python3
"""
Check audio device capabilities
"""

import sounddevice as sd

print("=" * 60)
print("Audio Devices Information")
print("=" * 60)

devices = sd.query_devices()

for idx, device in enumerate(devices):
    print(f"\nDevice {idx}: {device['name']}")
    print(f"  Max Input Channels:  {device['max_input_channels']}")
    print(f"  Max Output Channels: {device['max_output_channels']}")
    print(f"  Default Sample Rate: {device['default_samplerate']}")
    
    if 'H08A' in device['name'] or idx == 0:
        print(f"  ⭐ This is your H08A device!")

print("\n" + "=" * 60)
print("Default devices:")
print(f"  Input:  {sd.query_devices(kind='input')['name']}")
print(f"  Output: {sd.query_devices(kind='output')['name']}")
print("=" * 60)