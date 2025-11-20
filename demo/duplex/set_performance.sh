#!/bin/bash
# RP5 CPU Performance Mode Setup
# Run before starting full-duplex communication

set -e

echo "=================================================="
echo "🚀 RP5 CPU Performance Mode Setup"
echo "=================================================="
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "❌ This script requires sudo privileges"
    echo "   Please run: sudo bash $0"
    exit 1
fi

# Show current status
echo "📊 Current CPU Governor:"
for cpu in 0 1 2 3; do
    current=$(cat /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_governor)
    freq=$(cat /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_cur_freq)
    echo "   CPU${cpu}: ${current} @ ${freq} kHz"
done
echo ""

# Set to performance mode
echo "⚡ Setting all CPUs to performance mode..."
for cpu in 0 1 2 3; do
    echo performance > /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_governor
    echo "   ✅ CPU${cpu} → performance"
done
echo ""

# Verify new status
echo "✅ New CPU Governor:"
for cpu in 0 1 2 3; do
    current=$(cat /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_governor)
    freq=$(cat /sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_cur_freq)
    echo "   CPU${cpu}: ${current} @ ${freq} kHz"
done
echo ""

# Show expected frequency
max_freq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq)
echo "🎯 Expected max frequency: ${max_freq} kHz (2400 MHz for RP5)"
echo ""

echo "=================================================="
echo "✅ CPU Performance Mode Enabled"
echo "=================================================="
echo ""
echo "⚠️  Note: This setting will reset after reboot"
echo "   To make permanent, install systemd service:"
echo "   sudo cp rp5-performance.service /etc/systemd/system/"
echo "   sudo systemctl enable rp5-performance.service"
echo ""
echo "🎤 You can now start the communication script"
echo ""
