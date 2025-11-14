#!/usr/bin/env python3
"""
RP5-B Full-Duplex DEBUG Starter
================================

Interactive device selection for RP5-B
"""

import os
import sys
import subprocess
import sounddevice as sd

def list_audio_devices():
    """Display available audio devices"""
    print("\n" + "="*60)
    print("🎤🔊 Available Audio Devices")
    print("="*60)
    devices = sd.query_devices()
    
    valid_devices = []
    for i, device in enumerate(devices):
        in_ch = device['max_input_channels']
        out_ch = device['max_output_channels']
        if in_ch > 0 or out_ch > 0:
            print(f"\n[{i}] {device['name']}")
            print(f"    Input:  {in_ch} channels")
            print(f"    Output: {out_ch} channels")
            print(f"    Sample Rate: {device['default_samplerate']} Hz")
            valid_devices.append(i)
    
    print("="*60)
    return valid_devices

def select_device(prompt, valid_devices):
    """Interactive device selection"""
    while True:
        try:
            choice = int(input(f"\n{prompt}: "))
            if choice in valid_devices:
                return choice
            else:
                print(f"❌ Invalid device. Choose from: {valid_devices}")
        except ValueError:
            print("❌ Please enter a number")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled")
            sys.exit(0)

def main():
    print("\n" + "="*60)
    print("🚀 RP5-B Full-Duplex DEBUG Starter")
    print("="*60)
    print("\nRole: B (Client)")
    print("Peer: RP5-A")
    print("Mode: DEBUG (NO AI)")
    
    # List devices
    valid_devices = list_audio_devices()
    
    # Select devices
    print("\n📝 Select Audio Devices:")
    mic_device = select_device("🎤 Microphone device number", valid_devices)
    speaker_device = select_device("🔊 Speaker device number", valid_devices)
    
    # Confirm
    print("\n" + "="*60)
    print("✅ Configuration:")
    print(f"   Role: B")
    print(f"   Mic: Device {mic_device}")
    print(f"   Speaker: Device {speaker_device}")
    print(f"   Peer IP: 10.42.0.1 (RP5-A)")
    print(f"   Send Port: 9998 → RP5-A:9998")
    print(f"   Recv Port: 9999 ← RP5-A:9999")
    print("="*60)
    
    confirm = input("\n▶️  Start communication? [Y/n]: ").strip().lower()
    if confirm and confirm != 'y':
        print("👋 Cancelled")
        return
    
    # Run full-duplex DEBUG
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "rp5_full_duplex_debug.py")
    
    cmd = [
        sys.executable,
        main_script,
        "--role", "B",
        "--peer-ip", "10.42.0.1",
        "--mic-device", str(mic_device),
        "--speaker-device", str(speaker_device),
        "--send-port", "9998",
        "--recv-port", "9999"
    ]
    
    print("\n🔄 Starting full-duplex DEBUG communication...\n")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n👋 Stopped")

if __name__ == "__main__":
    main()
