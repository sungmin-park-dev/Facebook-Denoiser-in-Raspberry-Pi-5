#!/usr/bin/env python3
"""
Real-time 4-Stage Audio Pipeline
================================

Processing Chain:
1. High-Pass Filter (80Hz) - Remove low-frequency rumble
2. Impulse Noise Suppressor - Handle clicks/pops
3. AI Denoiser (Light-32-Depth4) - Core denoising
4. Soft Limiter - Prevent clipping

Hardware: H08A USB Audio (Device 1)
Target: RTF < 0.1 on Raspberry Pi 5
"""

import sounddevice as sd
import torch
import numpy as np
import time
import yaml
from pathlib import Path
from scipy import signal
from collections import deque
import threading
import queue
import warnings
import os

# Suppress warnings
os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')

# ========== Configuration Loading ==========
# Use custom config if provided, otherwise use default
if '--config' in sys.argv:
    parser_temp = argparse.ArgumentParser()
    parser_temp.add_argument('--config', type=str)
    args_temp, _ = parser_temp.parse_known_args()
    CONFIG_PATH = Path(args_temp.config) if args_temp.config else Path(__file__).parent.parent / 'configs' / 'filter_chain.yaml'
else:
    CONFIG_PATH = Path(__file__).parent.parent / 'configs' / 'filter_chain.yaml'

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)
    
print(f"📄 Using config: {CONFIG_PATH.name}")

# Audio settings
HARDWARE_SR = 48000
MODEL_SR = config['audio']['sample_rate']
CHUNK = 16000  # 333ms processing chunk

# ========== Audio Device Configuration ==========
# Priority: CLI args > Environment vars > Auto-detect > Default
import sys
import argparse

def list_audio_devices():
    """List all available audio devices"""
    print("\n" + "="*60)
    print("📱 Available Audio Devices:")
    print("="*60)
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        input_ch = device['max_input_channels']
        output_ch = device['max_output_channels']
        print(f"[{idx}] {device['name']}")
        print(f"    Input: {input_ch} ch | Output: {output_ch} ch")
    print("="*60 + "\n")

def auto_detect_audio_device(keywords=['H08A', 'USB', 'BLUETOOTH']):
    """
    Auto-detect audio device by keywords (case-insensitive)
    Priority: H08A > USB Audio > Bluetooth > First available
    """
    devices = sd.query_devices()
    
    # Try keywords in priority order
    for keyword in keywords:
        for idx, device in enumerate(devices):
            if keyword.upper() in device['name'].upper():
                # Check if device has both input and output
                if device['max_input_channels'] > 0 and device['max_output_channels'] > 0:
                    print(f"✅ Auto-detected: [{idx}] {device['name']}")
                    return idx
    
    # Fallback: First device with both input and output
    for idx, device in enumerate(devices):
        if device['max_input_channels'] > 0 and device['max_output_channels'] > 0:
            print(f"⚠️  Using fallback device: [{idx}] {device['name']}")
            return idx
    
    return None

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Real-time 4-Stage Audio Pipeline')
parser.add_argument('--list-devices', action='store_true', 
                    help='List all audio devices and exit')
parser.add_argument('--input', type=int, default=None,
                    help='Input device index (see --list-devices)')
parser.add_argument('--output', type=int, default=None,
                    help='Output device index (see --list-devices)')
parser.add_argument('--device', type=int, default=None,
                    help='Use same device for input and output')
parser.add_argument('--config', type=str, default=None,
                    help='Path to custom config file (default: audio_pipeline/configs/filter_chain.yaml)')

args = parser.parse_args()

# Handle --list-devices
if args.list_devices:
    list_audio_devices()
    sys.exit(0)

# Determine devices
if args.device is not None:
    # --device option: use same for input/output
    INPUT_DEVICE = OUTPUT_DEVICE = args.device
    print(f"✅ Manual selection: Device {args.device} (input + output)")
elif args.input is not None or args.output is not None:
    # Separate input/output
    INPUT_DEVICE = args.input if args.input is not None else auto_detect_audio_device()
    OUTPUT_DEVICE = args.output if args.output is not None else INPUT_DEVICE
    print(f"✅ Manual selection: Input={INPUT_DEVICE}, Output={OUTPUT_DEVICE}")
else:
    # Auto-detect
    detected = auto_detect_audio_device()
    INPUT_DEVICE = OUTPUT_DEVICE = detected
    
if INPUT_DEVICE is None or OUTPUT_DEVICE is None:
    print("❌ No suitable audio device found!")
    print("   Run with --list-devices to see available devices")
    sys.exit(1)

# ========== Filter Stage 1: High-Pass Filter ==========
class HighPassFilter:
    """Remove low-frequency rumble (<80Hz)"""
    def __init__(self, cutoff=80, order=4, sr=16000):
        self.sos = signal.butter(order, cutoff, 'hp', fs=sr, output='sos')
        self.zi = signal.sosfilt_zi(self.sos)
        
    def process(self, audio):
        filtered, self.zi = signal.sosfilt(self.sos, audio, zi=self.zi)
        return filtered

# ========== Filter Stage 2: Impulse Noise Suppressor ==========
class ImpulseNoiseSuppressor:
    """Suppress sudden clicks/pops"""
    def __init__(self, threshold_factor=3.0, window_size=5):
        self.threshold_factor = threshold_factor
        self.window_size = window_size
        self.history = deque(maxlen=window_size)
        
    def process(self, audio):
        # Calculate moving median
        self.history.append(np.median(np.abs(audio)))
        if len(self.history) < self.window_size:
            return audio
        
        median = np.median(list(self.history))
        threshold = median * self.threshold_factor
        
        # Clip extreme values
        output = np.clip(audio, -threshold, threshold)
        return output

# ========== Filter Stage 3: AI Denoiser ==========
class AIDenoiser:
    """Facebook Denoiser wrapper"""
    def __init__(self, model_path='models/current/best.th'):
        print(f"Loading AI model from {model_path}...")
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        model_class = checkpoint['class']
        self.model = model_class(*checkpoint['args'], **checkpoint['kwargs'])
        self.model.load_state_dict(checkpoint['state'])
        self.model.eval()
        
        # JIT compile for speed
        dummy_input = torch.randn(1, 1, CHUNK // 3)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model = torch.jit.trace(self.model, dummy_input)
        
        print("✅ AI model ready")
        
    def process(self, audio):
        x = torch.from_numpy(audio).float().unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            y = self.model(x)
        return y.squeeze().cpu().numpy()

# ========== Filter Stage 4: Soft Limiter ==========
class SoftLimiter:
    """Prevent clipping with soft limiting"""
    def __init__(self, threshold=0.8):
        self.threshold = threshold
        
    def process(self, audio):
        # Soft clip using tanh
        scale = self.threshold
        output = np.where(
            np.abs(audio) > self.threshold,
            scale * np.tanh(audio / scale),
            audio
        )
        return output

# ========== Filter Chain Manager ==========
class FilterChain:
    """Coordinate all 4 filter stages"""
    def __init__(self, config):
        self.filters = []
        
        # Stage 1: HPF
        if config['filters']['highpass']['enabled']:
            hpf = HighPassFilter(
                cutoff=config['filters']['highpass']['cutoff_freq'],
                order=config['filters']['highpass']['order'],
                sr=MODEL_SR
            )
            self.filters.append(('HPF', hpf))
            print("✅ Filter 1/4: High-Pass Filter (80Hz)")
        
        # Stage 2: Impulse Suppressor
        if config['filters']['impulse_suppressor']['enabled']:
            ins = ImpulseNoiseSuppressor(
                threshold_factor=config['filters']['impulse_suppressor']['threshold_factor'],
                window_size=config['filters']['impulse_suppressor']['window_size']
            )
            self.filters.append(('ImpulseSuppressor', ins))
            print("✅ Filter 2/4: Impulse Noise Suppressor")
        
        # Stage 3: AI Denoiser
        if config['filters']['ai_denoiser']['enabled']:
            model_path = config['filters']['ai_denoiser']['model_path']
            if model_path is None:
                model_path = 'models/current/best.th'
            denoiser = AIDenoiser(model_path)
            self.filters.append(('AIDenoiser', denoiser))
            print("✅ Filter 3/4: AI Denoiser (Light-32-Depth4)")
        
        # Stage 4: Soft Limiter
        if config['filters']['limiter']['enabled']:
            limiter = SoftLimiter(
                threshold=config['filters']['limiter']['threshold']
            )
            self.filters.append(('SoftLimiter', limiter))
            print("✅ Filter 4/4: Soft Limiter")
    
    def process(self, audio):
        """Run audio through all filters"""
        for name, filter_obj in self.filters:
            audio = filter_obj.process(audio)
        return audio

# ========== Initialize Filter Chain ==========
print("="*60)
print("🎛️  Initializing 4-Stage Audio Pipeline...")
print("="*60)
filter_chain = FilterChain(config)
print("="*60 + "\n")

# ========== Buffered Streaming Setup ==========
BUFFER_SIZE = 96000  # 2-second output buffer
output_buffer = deque(maxlen=BUFFER_SIZE)
buffer_lock = threading.Lock()
process_queue = queue.Queue(maxsize=10)

# Stats
chunk_count = 0
rtf_list = []
start_time = time.time()
processing = True

# ========== Processing Thread ==========
def processing_thread():
    """Background audio processing"""
    global chunk_count
    
    while processing:
        try:
            audio_data = process_queue.get(timeout=0.1)
            
            t0 = time.time()
            
            # Downsample: 48k → 16k
            audio_16k = signal.resample_poly(audio_data, 1, 3)
            
            # Run through 4-stage filter chain
            denoised = filter_chain.process(audio_16k)
            
            # Upsample: 16k → 48k
            output_48k = signal.resample_poly(denoised, 3, 1)
            
            # Add to output buffer
            with buffer_lock:
                for sample in output_48k:
                    if len(output_buffer) < BUFFER_SIZE:
                        output_buffer.append(sample)
            
            # Performance stats
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
    """Microphone input → processing queue"""
    if status:
        print(f"⚠️  Input: {status}")
    
    try:
        audio_data = indata[:, 0].copy()
        process_queue.put_nowait(audio_data)
    except queue.Full:
        pass

# ========== Output Callback ==========
def output_callback(outdata, frames, time_info, status):
    """Output buffer → speaker"""
    if status:
        print(f"⚠️  Output: {status}")
    
    with buffer_lock:
        for i in range(frames):
            if output_buffer:
                outdata[i, 0] = output_buffer.popleft()
            else:
                outdata[i, 0] = 0

# ========== Main Loop ==========
def main():
    global processing
    
    print("="*60)
    print(f"🎤 Input: Device {INPUT_DEVICE}")
    print(f"🔊 Output: Device {OUTPUT_DEVICE}")
    print(f"📦 Processing chunk: {CHUNK/HARDWARE_SR*1000:.0f}ms")
    print(f"🔄 Output buffer: {BUFFER_SIZE/HARDWARE_SR*1000:.0f}ms")
    print(f"⏱️  Initial latency: ~2 seconds (buffer fill)")
    print("="*60)
    print("\n🚀 Starting 4-stage filter chain...")
    print("   🎤 Speak continuously - output will be smooth!")
    print("   ⏳ Wait 2-3 seconds for buffer to fill...")
    print("   Press Ctrl+C to stop\n")

    # Start processing thread
    proc_thread = threading.Thread(target=processing_thread, daemon=True)
    proc_thread.start()

    try:
        # Input stream
        input_stream = sd.InputStream(
            samplerate=HARDWARE_SR,
            blocksize=CHUNK,
            device=INPUT_DEVICE,
            channels=1,
            dtype=np.float32,
            callback=input_callback
        )
        
        # Output stream
        output_stream = sd.OutputStream(
            samplerate=HARDWARE_SR,
            blocksize=1024,
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
    print(f"📊 Final Stats:")
    print(f"   Chunks processed: {chunk_count}")
    print(f"   Runtime: {time.time() - start_time:.1f}s")
    
    if len(rtf_list) > 5:
        stable_rtf = rtf_list[5:]
        print(f"   Avg RTF: {np.mean(stable_rtf):.3f}")
        print(f"   Max RTF: {np.max(stable_rtf):.3f}")
        print(f"   Target RTF < 0.1: {'✅ PASS' if np.mean(stable_rtf) < 0.1 else '❌ FAIL'}")
    
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
