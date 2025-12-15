#!/usr/bin/env python3
"""
RP5-A Modular Full-Duplex Starter (Public WiFi)
================================================

Interactive launcher with:
- Public WiFi connection check
- Dynamic peer IP detection (mDNS, auto-detect, manual)
- Audio device selection
- Environment setup

Usage:
    python demo/duplex_public_wifi/start_modular_a.py
    python demo/duplex_public_wifi/start_modular_a.py --peer-ip 10.249.98.123

    OR in VSCode: Click Run ▶
"""

import subprocess
import sys
import os
import time
import argparse
import socket
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

def resolve_mdns_hostname(hostname):
    """
    Resolve mDNS hostname (e.g., 'test2-desktop.local') to IP address

    Returns:
        IP address string or None if failed
    """
    print(f"{Colors.YELLOW}🔍 Resolving mDNS hostname: {hostname}{Colors.NC}")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"{Colors.GREEN}✅ Resolved {hostname} → {ip}{Colors.NC}")
        return ip
    except socket.gaierror:
        print(f"{Colors.RED}❌ Failed to resolve {hostname}{Colors.NC}")
        return None

def get_my_ip():
    """Get current device's IP address on wlan0"""
    result = run_cmd("ip -4 addr show wlan0 | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){3}'", check=False)
    return result if result else None

def detect_peer_ip_auto():
    """
    Auto-detect peer IP by scanning local network
    (Simple implementation - can be enhanced)
    """
    print(f"{Colors.YELLOW}🔍 Auto-detecting peer on local network...{Colors.NC}")
    my_ip = get_my_ip()
    if not my_ip:
        print(f"{Colors.RED}❌ Cannot detect own IP{Colors.NC}")
        return None

    # Extract network prefix (e.g., 10.249.55.x -> 10.249.55)
    prefix = '.'.join(my_ip.split('.')[:-1])
    print(f"{Colors.CYAN}Scanning {prefix}.x network...{Colors.NC}")

    # Simple ping sweep (limited range for speed)
    # In production, you might use nmap or arp-scan
    for i in range(1, 255):
        test_ip = f"{prefix}.{i}"
        if test_ip == my_ip:
            continue

        # Quick ping test (1 packet, 0.5s timeout)
        result = run_cmd(f"ping -c 1 -W 0.5 {test_ip} > /dev/null 2>&1 && echo OK", check=False)
        if result == "OK":
            print(f"{Colors.GREEN}✅ Found device at {test_ip}{Colors.NC}")
            confirm = input(f"{Colors.YELLOW}Use this as peer? (y/n): {Colors.NC}").strip().lower()
            if confirm == 'y':
                return test_ip

    print(f"{Colors.RED}❌ No peer found automatically{Colors.NC}")
    return None

def prompt_peer_ip_manual():
    """Prompt user to enter peer IP manually"""
    print(f"{Colors.YELLOW}📝 Manual IP Entry{Colors.NC}")
    while True:
        peer_ip = input(f"{Colors.CYAN}Enter peer IP address: {Colors.NC}").strip()
        if not peer_ip:
            continue

        # Validate IP format
        parts = peer_ip.split('.')
        if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            # Test connectivity
            print(f"{Colors.YELLOW}Testing connection to {peer_ip}...{Colors.NC}")
            result = run_cmd(f"ping -c 3 -W 2 {peer_ip}", check=False)
            if result:
                print(f"{Colors.GREEN}✅ Peer reachable at {peer_ip}{Colors.NC}")
                return peer_ip
            else:
                print(f"{Colors.RED}⚠️  Peer not responding to ping{Colors.NC}")
                retry = input(f"{Colors.YELLOW}Use anyway? (y/n): {Colors.NC}").strip().lower()
                if retry == 'y':
                    return peer_ip
        else:
            print(f"{Colors.RED}❌ Invalid IP format{Colors.NC}")

def resolve_peer_ip(config_peer_ip, cmdline_peer_ip=None):
    """
    Resolve peer IP with priority:
    1. Command-line argument
    2. Config file value (try mDNS if .local)
    3. Auto-detect
    4. Manual entry

    Returns:
        IP address string
    """
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}🌐 Resolving Peer IP Address{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}")

    # Priority 1: Command-line
    if cmdline_peer_ip:
        print(f"{Colors.GREEN}✅ Using command-line peer IP: {cmdline_peer_ip}{Colors.NC}")
        return cmdline_peer_ip

    # Priority 2: Config file (try mDNS if applicable)
    if config_peer_ip:
        if config_peer_ip.endswith('.local'):
            # Try mDNS resolution
            resolved_ip = resolve_mdns_hostname(config_peer_ip)
            if resolved_ip:
                return resolved_ip
            print(f"{Colors.YELLOW}⚠️  mDNS failed, trying other methods...{Colors.NC}")
        elif config_peer_ip != "null" and config_peer_ip != "":
            # Static IP from config
            print(f"{Colors.GREEN}✅ Using config peer IP: {config_peer_ip}{Colors.NC}")
            return config_peer_ip

    # Priority 3: Auto-detect
    print(f"{Colors.YELLOW}Attempting auto-detection...{Colors.NC}")
    auto_ip = detect_peer_ip_auto()
    if auto_ip:
        return auto_ip

    # Priority 4: Manual entry
    print(f"{Colors.YELLOW}⚠️  Auto-detection failed{Colors.NC}")
    return prompt_peer_ip_manual()

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

def check_public_wifi():
    """Check Public WiFi connection"""
    print(f"{Colors.YELLOW}📡 Checking Public WiFi connection...{Colors.NC}")

    # Check wlan0 is UP
    result = run_cmd("ip link show wlan0 | grep 'state UP'", check=False)
    if not result:
        print(f"{Colors.RED}❌ wlan0 is not UP{Colors.NC}")
        print(f"{Colors.YELLOW}💡 Connect to WiFi: nmcli device wifi connect <SSID> password <PASSWORD>{Colors.NC}")
        sys.exit(1)

    # Get current IP
    my_ip = get_my_ip()
    if not my_ip:
        print(f"{Colors.RED}❌ No IP address assigned to wlan0{Colors.NC}")
        print(f"{Colors.YELLOW}💡 Check WiFi connection{Colors.NC}")
        sys.exit(1)

    print(f"{Colors.GREEN}✅ WiFi Connected: {my_ip}{Colors.NC}")

    # Check for Client Isolation (important for public WiFi!)
    print(f"{Colors.CYAN}ℹ️  Make sure Client Isolation is DISABLED on the WiFi network{Colors.NC}")
    print(f"{Colors.CYAN}   Test with: ping <peer-ip> before running{Colors.NC}")

    return my_ip

def activate_venv(project_dir, venv_name):
    """Check venv"""
    print(f"{Colors.YELLOW}🐍 Checking Python environment...{Colors.NC}")

    venv_python = os.path.join(os.path.expanduser(project_dir), f"{venv_name}/bin/python")
    if not os.path.exists(venv_python):
        print(f"{Colors.RED}❌ venv not found: {venv_python}{Colors.NC}")
        sys.exit(1)

    python_version = run_cmd(f"{venv_python} --version")
    print(f"{Colors.GREEN}✅ {python_version} ({venv_name}){Colors.NC}")

def set_cpu_governor(mode: str) -> bool:
    """
    Set CPU governor mode

    Args:
        mode: 'performance' or 'ondemand'

    Returns:
        True if successful
    """
    try:
        cmd = f"echo {mode} | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ CPU governor set to: {mode}")
            return True
        else:
            print(f"⚠️  Failed to set CPU governor (may need sudo)")
            return False
    except Exception as e:
        print(f"⚠️  CPU governor error: {e}")
        return False

def get_cpu_governor() -> str:
    """Get current CPU governor mode"""
    try:
        with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'r') as f:
            return f.read().strip()
    except:
        return "unknown"

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='RP5-A Full-Duplex Starter (Public WiFi)')
    parser.add_argument('--peer-ip', type=str, help='Peer IP address (overrides config)')
    parser.add_argument('--config', type=str, default='configs/rp5a_public.yaml', help='Config file path')
    args = parser.parse_args()

    # RP5-A Configuration
    CONFIG = {
        "role": "A",
        "project_dir": "~/denoiser",
        "venv": "venv",
        "peer_ip": None,  # Will be resolved dynamically
        "mic_device": None,      # None = interactive
        "speaker_device": None,  # None = interactive
        "config_file": args.config,
    }

    print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}🚀 RP5-A Modular Full-Duplex Starter (Public WiFi){Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
    print()

    # ===== CPU Performance 모드 켜기 =====
    original_governor = get_cpu_governor()
    print(f"🔧 Current CPU governor: {original_governor}")

    if original_governor != "performance":
        print("⚡ Setting CPU to performance mode...")
        set_cpu_governor("performance")
    else:
        print("✅ Already in performance mode")
    print()
    # ====================================

    try:
        # 1. Public WiFi check
        my_ip = check_public_wifi()
        print()

        # 2. Load config to get peer_ip hint
        import yaml
        project_dir = os.path.expanduser(CONFIG['project_dir'])
        config_path = os.path.join(project_dir, f"demo/duplex_public_wifi/{CONFIG['config_file']}")

        if not os.path.exists(config_path):
            print(f"{Colors.RED}❌ Config file not found: {config_path}{Colors.NC}")
            sys.exit(1)

        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)

        config_peer_ip = yaml_config.get('peer_ip', None)

        # 3. Resolve peer IP
        CONFIG['peer_ip'] = resolve_peer_ip(config_peer_ip, args.peer_ip)
        print()

        # 4. Python venv
        activate_venv(CONFIG['project_dir'], CONFIG['venv'])
        print()

        # 5. Audio devices
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

        # 6. Launch
        print()
        print(f"{Colors.GREEN}🎤 Starting Modular Full-Duplex...{Colors.NC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        print(f"  Role: {CONFIG['role']}")
        print(f"  My IP: {my_ip}")
        print(f"  Peer IP: {CONFIG['peer_ip']}")
        print(f"  Mic: Device {CONFIG['mic_device']}")
        print(f"  Speaker: Device {CONFIG['speaker_device']}")
        print()
        print(f"{Colors.CYAN}🎛️  Press Enter to toggle processor (Bypass/AI){Colors.NC}")
        print(f"{Colors.CYAN}💡 Press 'q' + Enter to quit{Colors.NC}")
        print()

        venv_python = os.path.join(project_dir, f"{CONFIG['venv']}/bin/python")
        script_path = os.path.join(project_dir, "demo/duplex_public_wifi/rp5_full_duplex_modular.py")

        # Update YAML with resolved peer_ip and selected devices
        yaml_config['peer_ip'] = CONFIG['peer_ip']
        yaml_config['mic_device'] = CONFIG['mic_device']
        yaml_config['speaker_device'] = CONFIG['speaker_device']

        with open(config_path, 'w') as f:
            yaml.dump(yaml_config, f)

        # Run
        cmd = f"{venv_python} {script_path} --config {config_path}"
        subprocess.run(cmd, shell=True, check=True)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 Stopped{Colors.NC}")

    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()

    finally:
        # ===== CPU 원래대로 복구 =====
        if original_governor != "performance":
            print(f"\n🔧 Restoring CPU governor to: {original_governor}")
            set_cpu_governor(original_governor)
        # ==============================


if __name__ == "__main__":
    main()
