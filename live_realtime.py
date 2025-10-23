#!/usr/bin/env python3
"""
Real-time Audio Denoising for Raspberry Pi 5
Light-32-Depth4 Model, RTF < 1.0 Target
"""

import sounddevice as sd
import torch
import numpy as np
import time
from collections import deque

# ========== Configuration ==========
SAMPLE_RATE = 16000
CHUNK_SIZE = 4096  # 256ms @ 16kHz (시작은 큰 청크로 안정성 확보)
INPUT_DEVICE = 1   # USB Audio Device
OUTPUT_DEVICE = 5  # default
MODEL_PATH = 'models/best.th'

# ========== Model Loading ==========
print("Loading model...")
checkpoint = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
model_class = checkpoint['class']
model = model_class(*checkpoint['args'], **checkpoint['kwargs'])
model.load_state_dict(checkpoint['state'])
model.eval()
print(f"✅ Model loaded: {sum(p.numel() for p in model.parameters()):,} parameters")

# ========== Performance Monitoring ==========
rtf_history = deque(maxlen=100)  # 최근 100개 청크의 RTF
chunk_count = 0

# ========== Audio Callback ==========
def callback(indata, outdata, frames, time_info, status):
    global chunk_count
    
    if status:
        print(f"⚠️  Status: {status}")
    
    try:
        # Timing start
        start_time = time.time()
        
        # 1. Numpy → Tensor (batch_size=1, channels=1, samples=frames)
        audio_np = indata[:, 0]  # 모노 채널
        audio_tensor = torch.from_numpy(audio_np).float().unsqueeze(0).unsqueeze(0)
        
        # 2. Model Inference
        with torch.no_grad():
            denoised = model(audio_tensor)
        
        # 3. Tensor → Numpy
        output_np = denoised.squeeze().cpu().numpy()
        
        # 4. Output (모노 → 모노)
        outdata[:, 0] = output_np
        
        # Timing end & RTF calculation
        process_time = time.time() - start_time
        audio_duration = frames / SAMPLE_RATE
        rtf = process_time / audio_duration
        rtf_history.append(rtf)
        
        chunk_count += 1
        
        # 10초마다 통계 출력
        if chunk_count % int(10 * SAMPLE_RATE / CHUNK_SIZE) == 0:
            avg_rtf = np.mean(rtf_history)
            max_rtf = np.max(rtf_history)
            print(f"📊 Chunks: {chunk_count} | Avg RTF: {avg_rtf:.3f} | Max RTF: {max_rtf:.3f}")
        
    except Exception as e:
        print(f"❌ Error in callback: {e}")
        outdata.fill(0)

# ========== Stream Start ==========
print("\n" + "="*50)
print(f"🎤 Input Device: {INPUT_DEVICE} (USB Audio Device)")
print(f"🔊 Output Device: {OUTPUT_DEVICE} (default)")
print(f"📦 Chunk Size: {CHUNK_SIZE} samples ({CHUNK_SIZE/SAMPLE_RATE*1000:.1f}ms)")
print(f"🎯 Target RTF: < 1.0")
print("="*50 + "\n")

try:
    with sd.Stream(
        samplerate=SAMPLE_RATE,
        blocksize=CHUNK_SIZE,
        device=(INPUT_DEVICE, OUTPUT_DEVICE),
        channels=(1, 1),  # 모노 in/out
        dtype='float32',
        callback=callback,
        latency='low'  # 낮은 지연 시간 모드
    ):
        print("🚀 Real-time denoising started!")
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
except Exception as e:
    print(f"\n❌ Error: {e}")
