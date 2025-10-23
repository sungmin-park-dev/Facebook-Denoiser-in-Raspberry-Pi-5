#!/usr/bin/env python3
"""
Real-time Audio Denoising - Buffered Streaming with Original Denoiser Models
Smooth continuous output with acceptable latency
"""

import sounddevice as sd
import torch
import numpy as np
import time
from scipy import signal
import warnings
import os
from collections import deque
import threading
import queue

os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')

# ========== Configuration ==========
HARDWARE_SR = 48000
MODEL_SR = 16000
CHUNK = 16000  # 333ms @ 48kHz (처리 단위)
INPUT_DEVICE = 1   # H08A Audio: USB Audio (hw:1,0)
OUTPUT_DEVICE = 1  # H08A Audio: USB Audio (hw:1,0)

# 원본 denoiser 모델 선택 (하나를 선택하세요)
MODEL_NAME = 'dns48'      # 가장 가벼운 모델 (~2.5M params) ⭐ RP5 추천
# MODEL_NAME = 'dns64'      # 중간 모델 (~5.5M params) - RTF 1.9 (너무 느림)
# MODEL_NAME = 'master64'   # 가장 무거운 모델 (~14M params)

# 버퍼 설정
BUFFER_SIZE = 96000  # 2초 버퍼 (부드러운 출력)
output_buffer = deque(maxlen=BUFFER_SIZE)
buffer_lock = threading.Lock()

# 처리 큐
process_queue = queue.Queue(maxsize=10)

# ========== Model Loading ==========
print("=" * 60)
print(f"📦 Loading original denoiser model: {MODEL_NAME}")
print("=" * 60)

try:
    # torch.hub를 사용하여 원본 모델 로드
    torch.hub.set_dir('/home/test1/.cache/torch/hub')
    model = torch.hub.load('facebookresearch/denoiser', MODEL_NAME, force_reload=False)
    model.eval()
    
    # 모델 정보 출력
    total_params = sum(p.numel() for p in model.parameters())
    print(f"✅ Model loaded successfully!")
    print(f"   Parameters: {total_params:,} ({total_params/1e6:.2f}M)")
    print(f"   Model: {MODEL_NAME}")
    
    # JIT 컴파일 (성능 향상)
    print("\n🔧 Compiling model with TorchScript...")
    dummy_input = torch.randn(1, 1, CHUNK // 3)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = torch.jit.trace(model, dummy_input)
    print("✅ Model compiled\n")
    
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    print("\n💡 Troubleshooting:")
    print("   1. Check internet connection (first download)")
    print("   2. Try: pip install soundfile")
    print("   3. Clear cache: rm -rf ~/.cache/torch/hub")
    exit(1)

# ========== Stats ==========
chunk_count = 0
rtf_list = []
start_time = time.time()
processing = True

# ========== Processing Thread ==========
def processing_thread():
    """백그라운드에서 오디오 처리"""
    global chunk_count
    
    while processing:
        try:
            audio_data = process_queue.get(timeout=0.1)
            
            t0 = time.time()
            
            # Downsample: 48k → 16k
            audio_16k = signal.resample_poly(audio_data, 1, 3)
            
            # Model inference
            x = torch.from_numpy(audio_16k).float().unsqueeze(0).unsqueeze(0)
            with torch.no_grad():
                y = model(x)
            
            # Upsample: 16k → 48k
            denoised = signal.resample_poly(y.squeeze().cpu().numpy(), 3, 1)
            
            # 버퍼에 추가
            with buffer_lock:
                for sample in denoised:
                    if len(output_buffer) < BUFFER_SIZE:
                        output_buffer.append(sample)
            
            # Stats
            process_time = time.time() - t0
            rtf = process_time / (len(audio_16k) / MODEL_SR)
            rtf_list.append(rtf)
            chunk_count += 1
            
            if chunk_count % 30 == 0:
                elapsed = time.time() - start_time
                avg_rtf = np.mean(rtf_list[-30:])
                buffer_ms = len(output_buffer) / HARDWARE_SR * 1000
                print(f"[{elapsed:5.1f}s] Chunks: {chunk_count:3d} | RTF: {avg_rtf:.3f} | Buffer: {buffer_ms:.0f}ms")
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ Processing error: {e}")

# ========== Input Callback ==========
def input_callback(indata, frames, time_info, status):
    """마이크 입력 → 처리 큐에 추가"""
    if status:
        print(f"⚠️  Input: {status}")
    
    try:
        # 스테레오 → 모노 변환 (평균)
        if indata.shape[1] == 2:
            audio_data = np.mean(indata, axis=1)
        else:
            audio_data = indata[:, 0].copy()
        
        # 논블로킹으로 큐에 추가
        process_queue.put_nowait(audio_data)
    except queue.Full:
        pass  # 큐가 가득 차면 스킵

# ========== Output Callback ==========
def output_callback(outdata, frames, time_info, status):
    """버퍼에서 꺼내서 스피커로 출력"""
    if status:
        print(f"⚠️  Output: {status}")
    
    with buffer_lock:
        for i in range(frames):
            if output_buffer:
                outdata[i, 0] = output_buffer.popleft()
            else:
                outdata[i, 0] = 0  # 버퍼 비었으면 무음

# ========== Main ==========
def main():
    global processing
    
    print("=" * 60)
    print(f"🎤 Input: Device {INPUT_DEVICE}")
    print(f"🔊 Output: Device {OUTPUT_DEVICE}")
    print(f"📦 Processing chunk: {CHUNK/HARDWARE_SR*1000:.0f}ms")
    print(f"🔄 Output buffer: {BUFFER_SIZE/HARDWARE_SR*1000:.0f}ms")
    print(f"⏱️  Initial latency: ~2 seconds (buffer fill)")
    print("=" * 60)
    print(f"\n🚀 Starting buffered streaming with {MODEL_NAME}...")
    print("   🎤 Speak continuously - output will be smooth!")
    print("   ⏳ Wait 2-3 seconds for buffer to fill...")
    print("   Press Ctrl+C to stop\n")

    # 처리 스레드 시작
    proc_thread = threading.Thread(target=processing_thread, daemon=True)
    proc_thread.start()

    try:
        # 입력 스트림 (스테레오)
        input_stream = sd.InputStream(
            samplerate=HARDWARE_SR,
            blocksize=CHUNK,
            device=INPUT_DEVICE,
            channels=2,  # H08A는 스테레오
            dtype=np.float32,
            callback=input_callback
        )
        
        # 출력 스트림
        output_stream = sd.OutputStream(
            samplerate=HARDWARE_SR,
            blocksize=1024,  # 작은 청크로 부드러운 출력
            device=OUTPUT_DEVICE,
            channels=1,
            dtype=np.float32,
            callback=output_callback
        )
        
        with input_stream, output_stream:
            while True:
                sd.sleep(1000)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        processing = False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        processing = False

    # Final stats
    print(f"\n{'='*60}")
    print(f"📊 Final Stats ({MODEL_NAME}):")
    print(f"   Chunks processed: {chunk_count}")
    print(f"   Runtime: {time.time() - start_time:.1f}s")
    
    if len(rtf_list) > 5:
        stable_rtf = rtf_list[5:]
        print(f"   Avg RTF: {np.mean(stable_rtf):.3f}")
        print(f"   Max RTF: {np.max(stable_rtf):.3f}")
        print(f"   Min RTF: {np.min(stable_rtf):.3f}")
    
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()