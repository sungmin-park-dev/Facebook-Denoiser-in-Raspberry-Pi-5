## Phase 1: Mac ↔ RP5-A Communication - SUCCESS

### Test Results (Fri Oct 24 16:31:02 KST 2025)
- Mac IP: 10.249.55.35
- RP5-A IP: 10.249.77.83
- Status: ✅ Audio transmission working
- Codec: Opus 24kbps
- Model: Light-32-Depth4
- Device: Bluetooth (Device 5)

### Commands:
RP5: python scripts/rp5_receiver.py --port 5000 --device 5
Mac: export PYTHONPATH=$(pwd); python scripts/mac_sender.py --rp5-ip 10.249.77.83 --port 5000

