#!/usr/bin/env python3
"""
RP5-B Modular Full-Duplex Starter
==================================

Interactive launcher with:
- WiFi Direct check
- Git sync check
- Audio device selection
- Environment setup

Usage:
    python demo/duplex/start_modular_b.py
    
    OR in VSCode: Click Run ▶
"""

import subprocess
import sys
import os
import time
import sounddevice as sd

# Colors
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'

def run_cmd(cmd, check=True, capture=True):
    """Execute shell command"""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check,
            capture_output=capture, text=True
        )
        return result.stdout.strip() if capture else None
    except subprocess.CalledProcessError as e:
        if check:
            print(f"{Colors.RED}❌ Command failed: {cmd}{Colors.NC}")
            print(f"{Colors.RED}Error: {e}{Colors.NC}")
            sys.exit(1)
        return None

def select_audio_device(device_type="mic"):
    """Interactive audio device selection"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    if device_type == "mic":
        print(f"{Colors.CYAN}🎤 Available Microphone Devices:{Colors.NC}")
    else:
        print(f"{Colors.CYAN}🔊 Available Speaker Devices:{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    
    devices = sd.query_devices()
    valid_devices = []
    
    for i, device in enumerate(devices):
        in_ch = device['max_input_channels']
        out_ch = device['max_output_channels']
        
        if device_type == "mic" and in_ch > 0:
            print(f"[{i}] {device['name']}")
            print(f"    Input: {in_ch} ch, SR: {device['default_samplerate']:.0f} Hz")
            if 'H08A' in device['name'] or 'USB' in device['name']:
                print(f"    └─ 🎯 Recommended!")
            valid_devices.append(i)
        elif device_type == "speaker" and out_ch > 0:
            print(f"[{i}] {device['name']}")
            print(f"    Output: {out_ch} ch, SR: {device['default_samplerate']:.0f} Hz")
            if 'H08A' in device['name'] or 'USB' in device['name'] or 'Bluetooth' in device['name']:
                print(f"    └─ 🎯 Recommended!")
            valid_devices.append(i)
    
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    
    while True:
        try:
            choice = input(f"{Colors.YELLOW}Select {device_type} device: {Colors.NC}").strip()
            device_num = int(choice)
            if device_num in valid_devices:
                device_info = devices[device_num]
                print(f"{Colors.GREEN}✅ Selected: [{device_num}] {device_info['name']}{Colors.NC}")
                return device_num
            else:
                print(f"{Colors.RED}❌ Invalid. Choose from: {valid_devices}{Colors.NC}")
        except ValueError:
            print(f"{Colors.RED}❌ Enter a number{Colors.NC}")
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}👋 Cancelled{Colors.NC}")
            sys.exit(0)

def check_wifi_direct(my_ip, ssid, password):
    """Check WiFi Direct connection"""
    print(f"{Colors.YELLOW}📡 Checking WiFi Direct...{Colors.NC}")
    
    # Check wlan0 is UP
    result = run_cmd("ip link show wlan0 | grep 'state UP'", check=False)
    if not result:
        print(f"{Colors.RED}❌ wlan0 is not UP{Colors.NC}")
        print(f"{Colors.YELLOW}💡 Connecting to WiFi Direct...{Colors.NC}")
        run_cmd(f"nmcli device wifi connect {ssid} password {password}")
        time.sleep(3)
    
    # Check IP
    ip_result = run_cmd(f"ip addr show wlan0 | grep 'inet {my_ip}'", check=False)
    if not ip_result:
        print(f"{Colors.RED}❌ Expected IP {my_ip} not found{Colors.NC}")
        print(f"{Colors.YELLOW}💡 Retry connection: nmcli device wifi connect {ssid} password {password}{Colors.NC}")
        sys.exit(1)
    
    print(f"{Colors.GREEN}✅ WiFi Direct OK: {my_ip}{Colors.NC}")



def activate_venv(project_dir, venv_name):
    """Check venv"""
    print(f"{Colors.YELLOW}🐍 Checking Python environment...{Colors.NC}")
    
    venv_python = os.path.join(os.path.expanduser(project_dir), f"{venv_name}/bin/python")
    if not os.path.exists(venv_python):
        print(f"{Colors.RED}❌ venv not found: {venv_python}{Colors.NC}")
        sys.exit(1)
    
    python_version = run_cmd(f"{venv_python} --version")
    print(f"{Colors.GREEN}✅ {python_version} ({venv_name}){Colors.NC}")

def main():
    # RP5-B Configuration
    CONFIG = {
        "role": "B",
        "project_dir": "~/Facebook-Denoiser-in-Raspberry-Pi-5",
        "venv": "venv_denoiser",
        "peer_ip": "10.42.0.1",
        "my_ip": "10.42.0.224",
        "wifi_ssid": "RP5-Direct",
        "wifi_password": "tactical123",
        "mic_device": None,      # None = interactive
        "speaker_device": None,  # None = interactive
    }
    
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}🚀 RP5-B Modular Full-Duplex Starter{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
    print()
    
    try:
        # 1. WiFi Direct
        check_wifi_direct(CONFIG['my_ip'], CONFIG['wifi_ssid'], CONFIG['wifi_password'])
        print()
        
        # 2. Git sync --> Removed
        
        # 3. Python venv
        activate_venv(CONFIG['project_dir'], CONFIG['venv'])
        print()
        
        # 4. Audio devices
        if CONFIG['mic_device'] is None:
            print(f"{Colors.YELLOW}🎤 Microphone not configured{Colors.NC}")
            CONFIG['mic_device'] = select_audio_device("mic")
            print()
        else:
            print(f"{Colors.GREEN}✅ Using mic device: {CONFIG['mic_device']}{Colors.NC}")
        
        if CONFIG['speaker_device'] is None:
            print(f"{Colors.YELLOW}🔊 Speaker not configured{Colors.NC}")
            CONFIG['speaker_device'] = select_audio_device("speaker")
            print()
        else:
            print(f"{Colors.GREEN}✅ Using speaker device: {CONFIG['speaker_device']}{Colors.NC}")
        
        # 5. Launch
        print()
        print(f"{Colors.GREEN}🎤 Starting Modular Full-Duplex...{Colors.NC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        print(f"  Role: {CONFIG['role']}")
        print(f"  Peer: {CONFIG['peer_ip']}")
        print(f"  Mic: Device {CONFIG['mic_device']}")
        print(f"  Speaker: Device {CONFIG['speaker_device']}")
        print()
        print(f"{Colors.CYAN}🎛️  Press Enter to toggle processor (Bypass/AI){Colors.NC}")
        print(f"{Colors.CYAN}💡 Press 'q' + Enter to quit{Colors.NC}")
        print()
        
        project_dir = os.path.expanduser(CONFIG['project_dir'])
        venv_python = os.path.join(project_dir, f"{CONFIG['venv']}/bin/python")
        script_path = os.path.join(project_dir, "demo/duplex/rp5_full_duplex_modular.py")
        config_path = os.path.join(project_dir, "demo/duplex/configs/rp5b_modular.yaml")
        
        # Update YAML with selected devices
        import yaml
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
        
        yaml_config['mic_device'] = CONFIG['mic_device']
        yaml_config['speaker_device'] = CONFIG['speaker_device']
        
        with open(config_path, 'w') as f:
            yaml.dump(yaml_config, f)
        
        # Run
        cmd = f"{venv_python} {script_path} --config {config_path}"
        subprocess.run(cmd, shell=True, check=True)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 Stopped{Colors.NC}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()