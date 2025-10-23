#!/usr/bin/env python3
"""
Real-time Audio Denoising - Optimized for RP5
Larger chunks + Pre-allocated buffers
"""

import sounddevice as sd
import torch
import numpy as np
import time
from collections import deque
from scipy import signal

# ========== Configuration ==========
HARDWARE_SAMPLE_RATE = 48000
MODEL_SAMPLE_RATE = 16000
CHUNK_SIZE = 24576  # 512ms @ 48kHz (2배 증가 → latency 증가하지만 안정성 확보)
INPUT_DEVICE = 1
OUTPUT_DEVICE = 5
MODEL_PATH = 'models/best.th'

DOWNSAMPLE_FACTOR = 3
UPSAMPLE_FACTOR = 3

print(f"🔧 Optimized Configuration:")
print(f"   Chunk: {CHUNK_SIZE} samples = {CHUNK_SIZE/HARDWARE_SAMPLE_RATE*1000:.0f}ms")
print(f"   Resampling: {HARDWARE_SAMPLE_RATE}Hz ↔ {MODEL_SAMPLE_RATE}Hz")

# ========== Model Loading ==========
print("\nLoading model...")
checkpoint = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
model_class = checkpoint['class']
model = model_class(*checkpoint['args'], **checkpoint['kwargs'])
model.load_state_dict(checkpoint['state'])
model.eval()

# JIT Compile for faster inference
print("Compiling model with JIT...")
dummy_input = torch.randn(1, 1, CHUNK_SIZE // DOWNSAMPLE_FACTOR)
model = torch.jit.trace(model, dummy_input)
print(f"✅ Model ready: {sum(p.numel() for p in model.parameters()):,} parameters")

# ========== Performance Monitoring ==========
rtf_history = deque(maxlen=50)
chunk_count = 0
error_count = 0

# ========== Audio Callback ==========
def callback(indata, outdata, frames, time_info, status):
    global chunk_count, error_count
    
    if status:
        error_count += 1
        if error_count <= 5:  # 처음 5번만 출력
            print(f"⚠️  Buffer issue: {status}")
    
    try:
        start_time = time.time()
        
        # 1. Downsample: 48kHz → 16kHz
        audio_48k = indata[:, 0]
        audio_16k = signal.resample_poly(audio_48k, 1, DOWNSAMPLE_FACTOR)
        
        # 2. Model Inference
        audio_tensor = torch.from_numpy(audio_16k).float().unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            denoised_16k = model(audio_tensor)
        
        # 3. Upsample: 16kHz → 48kHz
        denoised_16k_np = denoised_16k.squeeze().cpu().numpy()
        denoised_48k = signal.resample_poly(denoised_16k_np, UPSAMPLE_FACTOR, 1)
        
        # 4. Output
        output_len = min(len(denoised_48k), frames)
        outdata[:output_len, 0] = denoised_48k[:output_len]
        if output_len < frames:
            outdata[output_len:, 0] = 0
        
        # RTF
        process_time = time.time() - start_time
        audio_duration = len(audio_16k) / MODEL_SAMPLE_RATE
        rtf = process_time / audio_duration
        rtf_history.append(rtf)
        
        chunk_count += 1
        
        # 통계 출력 (20초마다)
        if chunk_count % int(20 * HARDWARE_SAMPLE_RATE / CHUNK_SIZE) == 0:
            avg_rtf = np.mean(rtf_history)
            max_rtf = np.max(rtf_history)
            print(f"📊 {chunk_count} chunks | RTF: {avg_rtf:.3f} (max {max_rtf:.3f}) | Errors: {error_count}")
        
    except Exception as e:
        print(f"❌ Callback error: {e}")
        outdata.fill(0)

# ========== Stream Start ==========
print("\n" + "="*60)
print(f"🎤 Input: Device {INPUT_DEVICE} @ {HARDWARE_SAMPLE_RATE}Hz")
print(f"🔊 Output: Device {OUTPUT_DEVICE} @ {HARDWARE_SAMPLE_RATE}Hz")
print(f"⏱️  Latency: ~{CHUNK_SIZE/HARDWARE_SAMPLE_RATE*1000:.0f}ms")
print("="*60 + "\n")

try:
    with sd.Stream(
        samplerate=HARDWARE_SAMPLE_RATE,
        blocksize=CHUNK_SIZE,
        device=(INPUT_DEVICE, OUTPUT_DEVICE),
        channels=(1, 1),
        dtype='float32',
        callback=callback,
        latency='high'  # 안정성 우선
    ):
        print("🚀 Denoising active!")
        print("   🎤 Speak into microphone...")
        print("   Ctrl+C to stop\n")
        
        while True:
            sd.sleep(1000)
            
except KeyboardInterrupt:
    print("\n🛑 Stopping...\n")
    if rtf_history:
        print("📈 Final Stats:")
        print(f"   Chunks: {chunk_count}")
        print(f"   Avg RTF: {np.mean(rtf_history):.3f}")
        print(f"   Max RTF: {np.max(rtf_history):.3f}")
        print(f"   Buffer errors: {error_count}")
        print(f"   Runtime: {chunk_count * CHUNK_SIZE / HARDWARE_SAMPLE_RATE:.1f}s")
except Exception as e:
    print(f"\n❌ Stream error: {e}")
