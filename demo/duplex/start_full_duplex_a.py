#!/usr/bin/env python3
"""
RP5-A Full-Duplex Communication - Auto-Start Script

Usage: 
  VSCode: Click Run button (▶)
  Terminal: python demo/duplex/start_full_duplex_a.py

RP5-A specific configuration (Access Point mode)
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
        print(f"{Colors.YELLOW}💡 Setting up WiFi Direct hotspot...{Colors.NC}")
        
        if config['wifi_mode'] == 'hotspot':
            # Create hotspot
            run_cmd(f"nmcli device wifi hotspot ssid {config.get('wifi_ssid', 'RP5-Direct')} password {config.get('wifi_password', 'tactical123')} ifname wlan0")
            time.sleep(3)
            
            # Verify
            ip_result = run_cmd(f"ip addr show wlan0 | grep 'inet {config['my_ip']}'", check=False)
            if not ip_result:
                print(f"{Colors.RED}❌ Failed to set up hotspot{Colors.NC}")
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

def check_git(config):
    """Check Git repository status"""
    print(f"{Colors.YELLOW}📂 Checking Git repository...{Colors.NC}")
    
    project_dir = os.path.expanduser(config['project_dir'])
    
    if not os.path.exists(os.path.join(project_dir, '.git')):
        print(f"{Colors.RED}❌ Not a git repository: {project_dir}{Colors.NC}")
        sys.exit(1)
    
    # Get current branch and commit
    os.chdir(project_dir)
    branch = run_cmd("git branch --show-current")
    commit = run_cmd("git rev-parse --short HEAD")
    
    print(f"{Colors.GREEN}✅ Git: {branch} @ {commit}{Colors.NC}")
    
    # Check for uncommitted changes
    status = run_cmd("git status --porcelain", check=False)
    if status:
        print(f"{Colors.YELLOW}⚠️  Uncommitted changes detected{Colors.NC}")

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


# ============================================================
# 🎯 RP5-A CONFIGURATION
# ============================================================
if __name__ == "__main__":
    # Role A configuration
    ROLE = "A"
    CONFIG = {
        "role": "A",
        "project_dir": "~/denoiser",
        "venv": "venv",
        "peer_ip": "10.42.0.224",
        "my_ip": "10.42.0.1",
        "mic_device": 1,
        "speaker_device": 1,
        "send_port": 9999,  # Send to B:9999
        "recv_port": 9998,  # Receive from B:9998
        "wifi_mode": "hotspot",  # A is AP
        "wifi_ssid": "RP5-Direct",
        "wifi_password": "tactical123",
        "config_file": "demo/duplex/configs/rp5a_config.yaml",
    }
    
    main(ROLE, CONFIG)