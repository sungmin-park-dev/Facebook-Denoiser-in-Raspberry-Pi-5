import sounddevice as sd

print("Available devices:\n")
devices = sd.query_devices()

for i, dev in enumerate(devices):
    in_ch = dev['max_input_channels']
    out_ch = dev['max_output_channels']
    sr = dev['default_samplerate']
    
    status = []
    if in_ch > 0:
        status.append(f"IN:{in_ch}")
    if out_ch > 0:
        status.append(f"OUT:{out_ch}")
    
    marker = "✅" if out_ch > 0 else "  "
    print(f"{marker} [{i}] {dev['name']}")
    print(f"     {' '.join(status)} @ {sr}Hz")
    print()

print("\nRecommended output devices (OUT > 0):")
for i, dev in enumerate(devices):
    if dev['max_output_channels'] > 0:
        print(f"  Device {i}: {dev['name']}")