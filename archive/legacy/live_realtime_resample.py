#!/usr/bin/env python3
"""
Real-time Audio Denoising for Raspberry Pi 5 with Resampling
Hardware: 48kHz → Model: 16kHz → Hardware: 48kHz
"""

import sounddevice as sd
import torch
import numpy as np
import time
from collections import deque
from scipy import signal

# ========== Configuration ==========
HARDWARE_SAMPLE_RATE = 48000  # USB 마이크 샘플레이트
MODEL_SAMPLE_RATE = 16000     # 모델 학습 샘플레이트
CHUNK_SIZE = 12288            # 256ms @ 48kHz
INPUT_DEVICE = 1              # USB Audio Device
OUTPUT_DEVICE = 5             # default
MODEL_PATH = 'models/best.th'

# ========== Resampling Setup ==========
# 48kHz → 16kHz: 1/3 다운샘플
# 16kHz → 48kHz: 3x 업샘플
DOWNSAMPLE_FACTOR = HARDWARE_SAMPLE_RATE // MODEL_SAMPLE_RATE  # 3
UPSAMPLE_FACTOR = DOWNSAMPLE_FACTOR  # 3

print(f"Resampling: {HARDWARE_SAMPLE_RATE}Hz → {MODEL_SAMPLE_RATE}Hz (1/{DOWNSAMPLE_FACTOR})")

# ========== Model Loading ==========
print("Loading model...")
checkpoint = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
model_class = checkpoint['class']
model = model_class(*checkpoint['args'], **checkpoint['kwargs'])
model.load_state_dict(checkpoint['state'])
model.eval()
print(f"✅ Model loaded: {sum(p.numel() for p in model.parameters()):,} parameters")

# ========== Performance Monitoring ==========
rtf_history = deque(maxlen=100)
chunk_count = 0

# ========== Audio Callback ==========
def callback(indata, outdata, frames, time_info, status):
    global chunk_count
    
    if status:
        print(f"⚠️  Status: {status}")
    
    try:
        start_time = time.time()
        
        # 1. Input: 48kHz numpy array
        audio_48k = indata[:, 0]
        
        # 2. Downsample: 48kHz → 16kHz
        audio_16k = signal.resample_poly(audio_48k, 1, DOWNSAMPLE_FACTOR)
        
        # 3. Tensor conversion
        audio_tensor = torch.from_numpy(audio_16k).float().unsqueeze(0).unsqueeze(0)
        
        # 4. Model Inference @ 16kHz
        with torch.no_grad():
            denoised_16k = model(audio_tensor)
        
        # 5. Tensor → Numpy
        denoised_16k_np = denoised_16k.squeeze().cpu().numpy()
        
        # 6. Upsample: 16kHz → 48kHz
        denoised_48k = signal.resample_poly(denoised_16k_np, UPSAMPLE_FACTOR, 1)
        
        # 7. Output (길이 맞추기)
        output_len = min(len(denoised_48k), frames)
        outdata[:output_len, 0] = denoised_48k[:output_len]
        if output_len < frames:
            outdata[output_len:, 0] = 0
        
        # RTF calculation (16kHz 기준)
        process_time = time.time() - start_time
        audio_duration_16k = len(audio_16k) / MODEL_SAMPLE_RATE
        rtf = process_time / audio_duration_16k
        rtf_history.append(rtf)
        
        chunk_count += 1
        
        # 10초마다 통계
        if chunk_count % int(10 * HARDWARE_SAMPLE_RATE / CHUNK_SIZE) == 0:
            avg_rtf = np.mean(rtf_history)
            max_rtf = np.max(rtf_history)
            latency = CHUNK_SIZE / HARDWARE_SAMPLE_RATE * 1000
            print(f"📊 Chunks: {chunk_count} | RTF: {avg_rtf:.3f} (max: {max_rtf:.3f}) | Latency: {latency:.0f}ms")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        outdata.fill(0)

# ========== Stream Start ==========
print("\n" + "="*60)
print(f"🎤 Input Device: {INPUT_DEVICE} @ {HARDWARE_SAMPLE_RATE}Hz")
print(f"🔊 Output Device: {OUTPUT_DEVICE} @ {HARDWARE_SAMPLE_RATE}Hz")
print(f"🧠 Model Sample Rate: {MODEL_SAMPLE_RATE}Hz")
print(f"📦 Chunk Size: {CHUNK_SIZE} samples ({CHUNK_SIZE/HARDWARE_SAMPLE_RATE*1000:.1f}ms)")
print(f"🎯 Target RTF: < 1.0")
print("="*60 + "\n")

try:
    with sd.Stream(
        samplerate=HARDWARE_SAMPLE_RATE,
        blocksize=CHUNK_SIZE,
        device=(INPUT_DEVICE, OUTPUT_DEVICE),
        channels=(1, 1),
        dtype='float32',
        callback=callback,
        latency='low'
    ):
        print("🚀 Real-time denoising started!")
        print("   Speak into the microphone...")
        print("   Press Ctrl+C to stop...")
        
        while True:
            sd.sleep(1000)
            
except KeyboardInterrupt:
    print("\n\n🛑 Stopping...")
    if rtf_history:
        print(f"\n📈 Final Statistics:")
        print(f"   Total chunks: {chunk_count}")
        print(f"   Average RTF: {np.mean(rtf_history):.3f}")
        print(f"   Max RTF: {np.max(rtf_history):.3f}")
        print(f"   Min RTF: {np.min(rtf_history):.3f}")
        print(f"   Total time: {chunk_count * CHUNK_SIZE / HARDWARE_SAMPLE_RATE:.1f}s")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
