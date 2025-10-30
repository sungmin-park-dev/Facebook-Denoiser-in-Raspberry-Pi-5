#!/usr/bin/env python3
"""
RP5 Full-Duplex Communication - Unified Auto-Start Script

Usage: 
  1. Set ROLE = "A" or "B" below
  2. VSCode: Click Run button (▶)
  3. Terminal: python scripts/start_full_duplex.py

Configuration is automatic based on ROLE.
"""

import subprocess
import sys
import os
import time

# ============================================================
# 🎯 CONFIGURATION - CHANGE THIS!
# ============================================================
ROLE = "A"  # Change to "A" or "B"
# ============================================================

# Role-specific configuration
CONFIG = {
    "A": {
        "project_dir": "~/denoiser",
        "venv": "venv",
        "peer_ip": "10.42.0.224",
        "my_ip": "10.42.0.1",
        "mic_device": 1,
        "speaker_device": 1,
        "send_port": 9999,  # Send to B:9999
        "recv_port": 9998,  # Receive from B:9998
        "wifi_mode": "hotspot",  # A is AP
        "wifi_connection": "Hotspot",
        "config_file": "demo/duplex/configs/rp5a_config.yaml",
    },
    "B": {
        "project_dir": "~/Facebook-Denoiser-in-Raspberry-Pi-5",
        "venv": "venv_denoiser",
        "peer_ip": "10.42.0.1",
        "my_ip": "10.42.0.224",
        "mic_device": 1,
        "speaker_device": 1,
        "send_port": 9998,  # Send to A:9998
        "recv_port": 9999,  # Receive from A:9999
        "wifi_mode": "client",  # B is client
        "wifi_ssid": "RP5-Direct",
        "wifi_password": "tactical123",
        "config_file": "demo/duplex/configs/rp5b_config.yaml",
    }
}

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

def check_wifi_direct(config):
    """Check and setup WiFi Direct connection"""
    print(f"{Colors.YELLOW}📡 Checking WiFi Direct connection...{Colors.NC}")
    
    # Get current SSID
    current_ssid = run_cmd(
        "nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d':' -f2",
        check=False
    )
    
    if config['wifi_mode'] == "hotspot":
        # RP5-A: Start hotspot
        if current_ssid != "RP5-Direct":
            print(f"{Colors.YELLOW}⚠️  Not connected to RP5-Direct (current: {current_ssid}){Colors.NC}")
            print(f"{Colors.YELLOW}🔄 Disconnecting from current network...{Colors.NC}")
            
            if current_ssid:
                run_cmd(f'sudo nmcli connection down "{current_ssid}"', check=False)
            
            print(f"{Colors.YELLOW}📡 Starting WiFi Direct hotspot...{Colors.NC}")
            run_cmd(f'sudo nmcli connection up "{config["wifi_connection"]}"')
            
            time.sleep(2)
            
            # Verify connection
            ip = run_cmd("hostname -I | awk '{print $1}'")
            if ip != config['my_ip']:
                print(f"{Colors.RED}❌ Failed to start WiFi Direct!{Colors.NC}")
                print(f"{Colors.RED}Expected IP: {config['my_ip']}, Got: {ip}{Colors.NC}")
                sys.exit(1)
            
            print(f"{Colors.GREEN}✅ WiFi Direct hotspot started: {ip}{Colors.NC}")
        else:
            ip = run_cmd("hostname -I | awk '{print $1}'")
            print(f"{Colors.GREEN}✅ Already running hotspot: {ip}{Colors.NC}")
    
    else:
        # RP5-B: Connect as client
        if current_ssid != "RP5-Direct":
            print(f"{Colors.YELLOW}⚠️  Not connected to RP5-Direct (current: {current_ssid}){Colors.NC}")
            print(f"{Colors.YELLOW}🔄 Disconnecting from current network...{Colors.NC}")
            
            if current_ssid:
                run_cmd(f'sudo nmcli connection down "{current_ssid}"', check=False)
            
            print(f"{Colors.YELLOW}📡 Connecting to RP5-Direct...{Colors.NC}")
            run_cmd(f'sudo nmcli device wifi connect "{config["wifi_ssid"]}" password "{config["wifi_password"]}"')
            
            time.sleep(2)
            
            # Verify connection
            ip = run_cmd("hostname -I | awk '{print $1}'")
            if ip != config['my_ip']:
                print(f"{Colors.YELLOW}⚠️  Got IP: {ip} (expected {config['my_ip']}, but may vary){Colors.NC}")
            
            # Test connectivity to RP5-A
            print(f"{Colors.YELLOW}🔍 Testing connection to RP5-A ({config['peer_ip']})...{Colors.NC}")
            ping_result = run_cmd(f"ping -c 2 {config['peer_ip']}", check=False)
            
            if ping_result is None or "2 received" not in ping_result:
                print(f"{Colors.RED}❌ Cannot reach RP5-A at {config['peer_ip']}{Colors.NC}")
                sys.exit(1)
            
            print(f"{Colors.GREEN}✅ WiFi Direct connected: {ip}{Colors.NC}")
        else:
            ip = run_cmd("hostname -I | awk '{print $1}'")
            print(f"{Colors.GREEN}✅ Already connected to RP5-Direct: {ip}{Colors.NC}")
            
            # Still test connectivity
            print(f"{Colors.YELLOW}🔍 Testing connection to peer...{Colors.NC}")
            ping_result = run_cmd(f"ping -c 2 {config['peer_ip']}", check=False)
            
            if ping_result is None or "2 received" not in ping_result:
                print(f"{Colors.RED}❌ Cannot reach peer at {config['peer_ip']}{Colors.NC}")
                sys.exit(1)
            
            print(f"{Colors.GREEN}✅ Connection OK{Colors.NC}")

def check_git(config):
    """Check git status and pull if needed"""
    print(f"{Colors.YELLOW}🔍 Checking git status...{Colors.NC}")
    
    # Change to project directory
    project_dir = os.path.expanduser(config['project_dir'])
    os.chdir(project_dir)
    
    # Fetch latest
    run_cmd("git fetch origin main --quiet")
    
    # Compare local and remote
    local = run_cmd("git rev-parse @")
    remote = run_cmd("git rev-parse @{u}")
    
    if local != remote:
        print(f"{Colors.YELLOW}📥 Pulling latest changes...{Colors.NC}")
        run_cmd("git pull origin main")
        print(f"{Colors.GREEN}✅ Git updated{Colors.NC}")
    else:
        print(f"{Colors.GREEN}✅ Git up to date{Colors.NC}")

def activate_venv(config):
    """Activate virtual environment and set PYTHONPATH"""
    print(f"{Colors.YELLOW}🐍 Setting up Python environment...{Colors.NC}")
    
    project_dir = os.path.expanduser(config['project_dir'])
    
    # Set PYTHONPATH
    os.environ['PYTHONPATH'] = project_dir
    sys.path.insert(0, project_dir)
    
    print(f"{Colors.GREEN}✅ PYTHONPATH set: {project_dir}{Colors.NC}")

def run_full_duplex(config):
    """Run full-duplex communication"""
    print()
    print(f"{Colors.GREEN}🎤 Starting Full-Duplex Communication (Role {ROLE}){Colors.NC}")
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
    config_path = os.path.join(project_dir, config['config_file'])
    
    # Run with venv python
    cmd = f'{venv_python} {script_path} --config {config_path}'
    
    try:
        subprocess.run(cmd, shell=True, check=True)
    except KeyboardInterrupt:
        print()
        print(f"{Colors.YELLOW}🛑 Stopped by user{Colors.NC}")
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Error running script: {e}{Colors.NC}")
        sys.exit(1)

def main():
    """Main execution"""
    # Validate ROLE
    if ROLE not in ["A", "B"]:
        print(f"{Colors.RED}❌ Invalid ROLE: {ROLE}{Colors.NC}")
        print(f"{Colors.YELLOW}Please set ROLE = 'A' or 'B' at the top of this script{Colors.NC}")
        sys.exit(1)
    
    config = CONFIG[ROLE]
    
    print(f"{Colors.BLUE}{'='*50}{Colors.NC}")
    print(f"{Colors.BLUE}🚀 RP5-{ROLE} Full-Duplex Auto-Start{Colors.NC}")
    print(f"{Colors.BLUE}{'='*50}{Colors.NC}")
    print()
    
    try:
        # 1. Check WiFi Direct
        check_wifi_direct(config)
        print()
        
        # 2. Check Git
        check_git(config)
        print()
        
        # 3. Setup Python environment
        activate_venv(config)
        print()
        
        # 4. Run full-duplex
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

if __name__ == "__main__":
    main()
