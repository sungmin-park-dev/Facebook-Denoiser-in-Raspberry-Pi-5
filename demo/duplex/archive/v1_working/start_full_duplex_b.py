#!/usr/bin/env python3
"""
RP5-B Full-Duplex Communication - Auto-Start Script

Usage: 
  VSCode: Click Run button (▶)
  Terminal: python demo/duplex/start_full_duplex_b.py

RP5-B specific configuration (Client mode)
"""

import subprocess
import sys
import os
import time

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def run_cmd(cmd, check=True, capture=True):
    """Run shell command and return output"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=check,
            capture_output=capture,
            text=True
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
    import sounddevice as sd
    
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
        
        # Filter based on device type
        if device_type == "mic" and in_ch > 0:
            print(f"[{i}] {device['name']}")
            print(f"    Input: {in_ch} ch, Sample Rate: {device['default_samplerate']:.0f} Hz")
            
            # Highlight H08A or USB devices
            if 'H08A' in device['name'] or 'USB' in device['name']:
                print(f"    └─ 🎯 Recommended device!")
            
            valid_devices.append(i)
            
        elif device_type == "speaker" and out_ch > 0:
            print(f"[{i}] {device['name']}")
            print(f"    Output: {out_ch} ch, Sample Rate: {device['default_samplerate']:.0f} Hz")
            
            # Highlight H08A or USB devices
            if 'H08A' in device['name'] or 'USB' in device['name']:
                print(f"    └─ 🎯 Recommended device!")
            
            valid_devices.append(i)
    
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    
    # Get user selection
    while True:
        try:
            choice = input(f"{Colors.YELLOW}Select {device_type} device number: {Colors.NC}").strip()
            device_num = int(choice)
            
            if device_num in valid_devices:
                device_info = devices[device_num]
                print(f"{Colors.GREEN}✅ Selected: [{device_num}] {device_info['name']}{Colors.NC}")
                return device_num
            else:
                print(f"{Colors.RED}❌ Invalid device number. Please choose from the list.{Colors.NC}")
                
        except ValueError:
            print(f"{Colors.RED}❌ Please enter a valid number.{Colors.NC}")
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}🛑 Selection cancelled{Colors.NC}")
            sys.exit(0)
        except Exception as e:
            print(f"{Colors.RED}❌ Error: {e}{Colors.NC}")

def setup_audio_devices(config):
    """Setup audio devices - interactive if None, otherwise use config"""
    if config['mic_device'] is None:
        print(f"\n{Colors.YELLOW}🎤 Microphone device not configured{Colors.NC}")
        config['mic_device'] = select_audio_device("mic")
        print()
    else:
        print(f"{Colors.GREEN}✅ Using configured mic device: {config['mic_device']}{Colors.NC}")
    
    if config['speaker_device'] is None:
        print(f"{Colors.YELLOW}🔊 Speaker device not configured{Colors.NC}")
        config['speaker_device'] = select_audio_device("speaker")
        print()
    else:
        print(f"{Colors.GREEN}✅ Using configured speaker device: {config['speaker_device']}{Colors.NC}")
    
    return config

def check_wifi_direct(config):
    """Check WiFi Direct connection"""
    print(f"{Colors.YELLOW}📡 Checking WiFi Direct connection...{Colors.NC}")
    
    # Check if wlan0 is up
    result = run_cmd("ip link show wlan0 | grep 'state UP'", check=False)
    if not result:
        print(f"{Colors.RED}❌ wlan0 is not UP{Colors.NC}")
        sys.exit(1)
    
    # Check IP address
    ip_result = run_cmd(f"ip addr show wlan0 | grep 'inet {config['my_ip']}'", check=False)
    if not ip_result:
        print(f"{Colors.RED}❌ Expected IP {config['my_ip']} not found{Colors.NC}")
        print(f"{Colors.YELLOW}💡 Connecting to WiFi Direct...{Colors.NC}")
        
        if config['wifi_mode'] == 'client':
            # Connect to AP
            run_cmd(f"nmcli device wifi connect {config['wifi_ssid']} password {config['wifi_password']}")
            time.sleep(3)
            
            # Verify
            ip_result = run_cmd(f"ip addr show wlan0 | grep 'inet {config['my_ip']}'", check=False)
            if not ip_result:
                print(f"{Colors.RED}❌ Failed to connect to WiFi Direct{Colors.NC}")
                sys.exit(1)
    
    print(f"{Colors.GREEN}✅ WiFi Direct: {config['my_ip']} (Mode: {config['wifi_mode']}){Colors.NC}")
    
    # Ping peer
    print(f"{Colors.YELLOW}📡 Checking peer connectivity...{Colors.NC}")
    ping_result = run_cmd(f"ping -c 1 -W 2 {config['peer_ip']}", check=False)
    if not ping_result:
        print(f"{Colors.RED}❌ Cannot reach peer {config['peer_ip']}{Colors.NC}")
        print(f"{Colors.YELLOW}⚠️  Continuing anyway (peer may not be ready yet)...{Colors.NC}")
    else:
        print(f"{Colors.GREEN}✅ Peer reachable: {config['peer_ip']}{Colors.NC}")


def activate_venv(config):
    """Check and activate Python virtual environment"""
    print(f"{Colors.YELLOW}🐍 Checking Python environment...{Colors.NC}")
    
    project_dir = os.path.expanduser(config['project_dir'])
    venv_path = os.path.join(project_dir, config['venv'])
    venv_python = os.path.join(venv_path, 'bin', 'python')
    
    if not os.path.exists(venv_python):
        print(f"{Colors.RED}❌ Virtual environment not found: {venv_path}{Colors.NC}")
        sys.exit(1)
    
    # Check Python version
    python_version = run_cmd(f"{venv_python} --version")
    print(f"{Colors.GREEN}✅ Python: {python_version}{Colors.NC}")
    print(f"{Colors.GREEN}   venv: {config['venv']}{Colors.NC}")

def run_full_duplex(config):
    """Run full-duplex communication"""
    print()
    print(f"{Colors.GREEN}🎤 Starting Full-Duplex Communication (Role {config['role']}){Colors.NC}")
    print(f"{Colors.GREEN}{'='*50}{Colors.NC}")
    print(f"{Colors.CYAN}Configuration:{Colors.NC}")
    print(f"  Peer IP: {config['peer_ip']}")
    print(f"  Send → {config['peer_ip']}:{config['send_port']}")
    print(f"  Recv ← 0.0.0.0:{config['recv_port']}")
    print(f"  Mic Device: {config['mic_device']}")
    print(f"  Speaker Device: {config['speaker_device']}")
    print()
    print("Press Ctrl+C to stop...")
    print()
    
    project_dir = os.path.expanduser(config['project_dir'])
    venv_python = os.path.join(project_dir, f"{config['venv']}/bin/python")
    script_path = os.path.join(project_dir, "demo/duplex/rp5_full_duplex.py")
    
    # Build command with explicit parameters
    cmd = (
        f'{venv_python} {script_path} '
        f'--role {config["role"]} '
        f'--peer-ip {config["peer_ip"]} '
        f'--mic-device {config["mic_device"]} '
        f'--speaker-device {config["speaker_device"]} '
        f'--send-port {config["send_port"]} '
        f'--recv-port {config["recv_port"]}'
    )
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print()
        print(f"{Colors.YELLOW}🛑 Stopped by user{Colors.NC}")
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Error running script: {e}{Colors.NC}")
        sys.exit(1)

def main(role, config):
    """Main execution"""
    print(f"{Colors.BLUE}{'='*50}{Colors.NC}")
    print(f"{Colors.BLUE}🚀 RP5-{role} Full-Duplex Auto-Start{Colors.NC}")
    print(f"{Colors.BLUE}{'='*50}{Colors.NC}")
    print()
    
    try:
        # 1. Check WiFi Direct
        check_wifi_direct(config)
        print()
        
        # 2. Git sync --> Removed
        
        # 3. Setup Python environment
        activate_venv(config)
        print()
        
        # 4. Setup audio devices (interactive if None)
        config = setup_audio_devices(config)
        print()
        
        # 5. Run full-duplex
        run_full_duplex(config)
        
    except KeyboardInterrupt:
        print()
        print(f"{Colors.YELLOW}🛑 Stopped by user{Colors.NC}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}❌ Unexpected error: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ============================================================
# 🎯 RP5-B CONFIGURATION
# ============================================================
if __name__ == "__main__":
    ROLE = "B"
    CONFIG = {
        "role": "B",
        "project_dir": "~/Facebook-Denoiser-in-Raspberry-Pi-5",
        "venv": "venv_denoiser",
        "peer_ip": "10.42.0.1",
        "my_ip": "10.42.0.224",
        "mic_device": None,      # None = 대화형 선택, 숫자 = 자동 진행
        "speaker_device": None,  # None = 대화형 선택, 숫자 = 자동 진행
        "send_port": 9998,
        "recv_port": 9999,
        "wifi_mode": "client",
        "wifi_ssid": "RP5-Direct",
        "wifi_password": "tactical123",
        "config_file": "demo/duplex/configs/rp5b_config.yaml",
    }
    
    main(ROLE, CONFIG)