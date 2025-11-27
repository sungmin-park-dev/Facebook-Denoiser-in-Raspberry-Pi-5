#!/usr/bin/env python3
"""
Real-time AI Denoiser Toggle Demo - Simplified
==============================================

Controls:
- Press ENTER to toggle AI ON/OFF
- Type 'q' + ENTER to quit
"""

import sounddevice as sd
import torch
import numpy as np
import time
from scipy import signal
from collections import deque
import threading
import queue
import warnings
import os
import sys
import select

os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')

# ========== Configuration ==========
HARDWARE_SR = 48000
MODEL_SR = 16000
CHUNK = 16000
MODEL_PATH = 'models/current/best.th'

# ========== Auto-detect Audio Device ==========
def auto_detect_audio_device(keywords=['H08A', 'USB', 'BLUETOOTH']):
    devices = sd.query_devices()
    for keyword in keywords:
        for idx, device in enumerate(devices):
            if keyword.upper() in device['name'].upper():
                if device['max_input_channels'] > 0 and device['max_output_channels'] > 0:
                    print(f"✅ Auto-detected: [{idx}] {device['name']}")
                    return idx
    
    for idx, device in enumerate(devices):
        if device['max_input_channels'] > 0 and device['max_output_channels'] > 0:
            print(f"⚠️  Using fallback: [{idx}] {device['name']}")
            return idx
    return None

INPUT_DEVICE = OUTPUT_DEVICE = auto_detect_audio_device()

if INPUT_DEVICE is None:
    print("❌ No suitable audio device found!")
    sys.exit(1)

# ========== Model Loading ==========
print("\n" + "="*60)
print("📦 Loading AI model...")
checkpoint = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
model = checkpoint['class'](*checkpoint['args'], **checkpoint['kwargs'])
model.load_state_dict(checkpoint['state'])
model.eval()

dummy_input = torch.randn(1, 1, CHUNK // 3)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    model = torch.jit.trace(model, dummy_input)

print("✅ AI model ready")
print("="*60 + "\n")

# ========== Global State ==========
BUFFER_SIZE = 96000
output_buffer = deque(maxlen=BUFFER_SIZE)
buffer_lock = threading.Lock()
process_queue = queue.Queue(maxsize=10)

chunk_count = 0
rtf_list = []
start_time = time.time()
processing = True

# AI State
ai_enabled = True
ai_lock = threading.Lock()

# ========== Simple Input Handler ==========
def input_thread():
    """Non-blocking input handler"""
    global ai_enabled, processing
    
    print("💬 Controls:")
    print("   Press ENTER       - Toggle AI ON/OFF")
    print("   Type 'q' + ENTER  - Quit")
    print()
    
    while processing:
        try:
            # Non-blocking check for input
            if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                line = sys.stdin.readline().strip().lower()
                
                if line == 'q' or line == 'quit':
                    print("\n🛑 Quit requested...")
                    processing = False
                    break
                else:
                    # Any other input (including empty = ENTER) toggles AI
                    with ai_lock:
                        ai_enabled = not ai_enabled
                        status = "🟢 ON " if ai_enabled else "🔴 OFF"
                        print(f"\n{'='*60}")
                        print(f"AI Denoiser: {status}")
                        print(f"{'='*60}\n")
        except Exception as e:
            # Fallback for systems without select
            time.sleep(0.1)

# ========== Processing Thread ==========
def processing_thread():
    global chunk_count
    
    while processing:
        try:
            audio_data = process_queue.get(timeout=0.1)
            
            t0 = time.time()
            
            audio_16k = signal.resample_poly(audio_data, 1, 3)
            
            with ai_lock:
                current_ai_state = ai_enabled
            
            if current_ai_state:
                x = torch.from_numpy(audio_16k).float().unsqueeze(0).unsqueeze(0)
                with torch.no_grad():
                    y = model(x)
                denoised = y.squeeze().cpu().numpy()
            else:
                denoised = audio_16k
            
            output_48k = signal.resample_poly(denoised, 3, 1)
            
            with buffer_lock:
                for sample in output_48k:
                    if len(output_buffer) < BUFFER_SIZE:
                        output_buffer.append(sample)
            
            process_time = time.time() - t0
            rtf = process_time / (len(audio_16k) / MODEL_SR)
            rtf_list.append(rtf)
            chunk_count += 1
            
            if chunk_count % 30 == 0:
                elapsed = time.time() - start_time
                avg_rtf = np.mean(rtf_list[-30:])
                buffer_ms = len(output_buffer) / HARDWARE_SR * 1000
                ai_status = "🟢 ON " if current_ai_state else "🔴 OFF"
                print(f"[{elapsed:5.1f}s] AI: {ai_status} | RTF: {avg_rtf:.3f} | Buffer: {buffer_ms:.0f}ms")
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ Error: {e}")

# ========== Audio Callbacks ==========
def input_callback(indata, frames, time_info, status):
    if status:
        print(f"⚠️  Input: {status}")
    try:
        process_queue.put_nowait(indata[:, 0].copy())
    except queue.Full:
        pass

def output_callback(outdata, frames, time_info, status):
    if status:
        print(f"⚠️  Output: {status}")
    with buffer_lock:
        for i in range(frames):
            outdata[i, 0] = output_buffer.popleft() if output_buffer else 0

# ========== Main ==========
def main():
    global processing
    
    print("="*60)
    print("🎤 Input: Device", INPUT_DEVICE)
    print("🔊 Output: Device", OUTPUT_DEVICE)
    print("🎛️  AI Denoiser: 🟢 ON (press ENTER to toggle)")
    print("="*60)
    print("\n🚀 Starting demo...")
    print("   🎤 Speak to hear the difference")
    print("   ⌨️  Press ENTER to toggle AI ON/OFF")
    print("   ❌ Type 'q' + ENTER to quit\n")

    proc_thread = threading.Thread(target=processing_thread, daemon=True)
    proc_thread.start()
    
    inp_thread = threading.Thread(target=input_thread, daemon=True)
    inp_thread.start()

    try:
        input_stream = sd.InputStream(
            samplerate=HARDWARE_SR,
            blocksize=CHUNK,
            device=INPUT_DEVICE,
            channels=1,
            dtype=np.float32,
            callback=input_callback
        )
        
        output_stream = sd.OutputStream(
            samplerate=HARDWARE_SR,
            blocksize=1024,
            device=OUTPUT_DEVICE,
            channels=1,
            dtype=np.float32,
            callback=output_callback
        )
        
        with input_stream, output_stream:
            while processing:
                sd.sleep(1000)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        processing = False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        processing = False

    print(f"\n{'='*60}")
    print(f"📊 Session complete")
    print(f"   Runtime: {time.time() - start_time:.1f}s")
    if len(rtf_list) > 5:
        print(f"   Avg RTF: {np.mean(rtf_list[5:]):.3f}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
