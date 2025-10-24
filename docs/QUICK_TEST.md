# Quick Test Commands: Mac ↔ RP5-A Communication

## 🎯 Prerequisites
- Mac and RP5-A on same WiFi network
- RP5-A IP: 10.249.77.83
- Mac IP: 10.249.55.35

---

## 📱 RP5-A Terminal (Execute FIRST)

```bash
cd /home/test1/denoiser
source /home/test1/venv/bin/activate
python scripts/rp5_receiver.py --port 5000 --device 5
```

**Expected Output:**
```
✅ OpusCodec initialized:
   Sample rate: 16000 Hz
   Channels: 1
   Bitrate: 16000 bps
   Frame size: 320 samples (20ms)
✅ RP5AudioReceiver initialized:
   Listening on port: 5000
   Speaker device: 5
   Buffer size: 10 frames
👂 Listening on port 5000...
Press Ctrl+C to stop...
```

---

## 💻 Mac Terminal (Execute AFTER RP5 is listening)

```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5
conda activate denoiser_modern
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python scripts/mac_sender.py --rp5-ip 10.249.77.83 --port 5000
```

**Expected Output:**
```
✅ OpusCodec initialized:
   Sample rate: 16000 Hz
   Channels: 1
   Bitrate: 16000 bps
   Frame size: 320 samples (20ms)
🤖 Loading Light-32-Depth4...
📂 Loading Light-32-Depth4 from models/current/best.th
✅ Model loaded: Light-32-Depth4
   Description: Optimized for RP5 (RTF 0.092)
   Parameters: 434K
   Device: cpu
✅ MacAudioSender initialized:
   Target: 10.249.77.83:5000
   Mic device: default
   Model: Light-32-Depth4
🎙️ Starting audio capture...
📡 Sending to 10.249.77.83:5000
Press Ctrl+C to stop...
```

---

## 🧪 Testing

1. **Start RP5 receiver** (wait for "Listening on port 5000...")
2. **Start Mac sender** (wait for "Sending to...")
3. **Speak into Mac microphone**
4. **Listen on RP5 Bluetooth speaker**
5. **Check statistics** (printed every 5 seconds)

---

## 🛑 Stop Testing

- Press `Ctrl+C` on both terminals
- Statistics will be displayed

---

## 🐛 Troubleshooting

### No audio output on RP5
```bash
# Check device list
python scripts/rp5_receiver.py --list-devices

# Try different device
python scripts/rp5_receiver.py --port 5000 --device [DEVICE_ID]
```

### Connection refused
```bash
# Check RP5 IP
ip addr show wlan0 | grep "inet "

# Update Mac command with correct IP
python scripts/mac_sender.py --rp5-ip [CORRECT_IP] --port 5000
```

### PYTHONPATH error on Mac
```bash
# Re-export before running
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## 📊 Success Criteria

✅ RP5 shows: "📡 Connected to 10.249.55.35:XXXXX"
✅ Mac shows: "📊 Sent XXX packets in X.Xs"
✅ Audio is heard on RP5 speaker
✅ Latency < 200ms
✅ No buffer underruns

---

Last Updated: 2025-10-24
