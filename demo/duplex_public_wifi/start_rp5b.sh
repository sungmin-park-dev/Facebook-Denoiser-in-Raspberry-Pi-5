#!/bin/bash
# RP5-B Integrated Launch Script
# Automatically sets performance mode and starts communication

set -e

PROJECT_DIR="/home/test2/Facebook-Denoiser-in-Raspberry-Pi-5"
VENV_PYTHON="${PROJECT_DIR}/venv_denoiser/bin/python"
SCRIPT_PATH="${PROJECT_DIR}/demo/duplex/rp5_full_duplex_modular.py"
CONFIG_PATH="${PROJECT_DIR}/demo/duplex/configs/rp5b_modular.yaml"

echo "=================================================="
echo "🚀 RP5-B Full-Duplex Launch"
echo "=================================================="
echo ""

# ===== Step 1: CPU Performance Mode =====
echo "⚡ Step 1: Setting CPU to Performance Mode"
echo "---------------------------------------------------"

if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Not running as sudo, CPU governor may not be optimal"
    echo "   Recommend: sudo bash $0"
    echo ""
else
    # Show current
    echo "Current:"
    for cpu in 0 1 2 3; do
        current=$(cat /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_governor)
        echo "  CPU${cpu}: ${current}"
    done
    
    # Set performance
    echo ""
    echo "Setting to performance..."
    for cpu in 0 1 2 3; do
        echo performance > /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_governor
    done
    
    # Verify
    echo "Verified:"
    for cpu in 0 1 2 3; do
        current=$(cat /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_governor)
        echo "  CPU${cpu}: ${current} ✅"
    done
    echo ""
fi

# ===== Step 2: Launch Communication =====
echo "⚡ Step 2: Starting Full-Duplex Communication"
echo "---------------------------------------------------"
echo "  Role: RP5-B (Client)"
echo "  Config: rp5b_modular.yaml"
echo "  Buffer: 5 frames"
echo ""
echo "🎛️  Press Enter to toggle processor (Bypass/AI)"
echo "💡 Press 'q' + Enter to quit"
echo ""
echo "=================================================="
echo ""

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment not found: $VENV_PYTHON"
    echo "   Please create venv first"
    exit 1
fi

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Script not found: $SCRIPT_PATH"
    exit 1
fi

# Launch
$VENV_PYTHON $SCRIPT_PATH --config $CONFIG_PATH

# ===== Cleanup: Restore CPU Governor =====
if [ "$EUID" -eq 0 ]; then
    echo ""
    echo "🔧 Restoring CPU governor to ondemand..."
    for cpu in 0 1 2 3; do
        echo ondemand > /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_governor
    done
    echo "✅ CPU governor restored"
fi
