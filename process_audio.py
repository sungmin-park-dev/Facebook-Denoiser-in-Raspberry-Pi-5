#!/usr/bin/env python3
"""
Offline Audio Processing - .wav File Denoising
==============================================

Process .wav files through the 4-stage filter chain:
1. High-Pass Filter (60Hz)
2. Impulse Noise Suppressor (disabled by default)
3. AI Denoiser (Light-32-Depth4)
4. Soft Limiter

Usage:
    python process_audio.py input.wav output.wav
    python process_audio.py input.wav output.wav --config filter_chain_optimized.yaml
"""

import torch
import numpy as np
import argparse
from pathlib import Path
from scipy import signal
from scipy.io import wavfile
import yaml
import warnings
from collections import deque

warnings.filterwarnings('ignore')

# ========== Filter Implementations ==========

class HighPassFilter:
    """Remove low-frequency rumble (<60Hz)"""
    def __init__(self, cutoff=60, order=2, sr=16000):
        self.sos = signal.butter(order, cutoff, 'hp', fs=sr, output='sos')
        self.zi = signal.sosfilt_zi(self.sos)
        
    def process(self, audio):
        filtered, self.zi = signal.sosfilt(self.sos, audio, zi=self.zi)
        return filtered

class ImpulseNoiseSuppressor:
    """Suppress sudden clicks/pops"""
    def __init__(self, threshold_factor=10.0, window_size=3):
        self.threshold_factor = threshold_factor
        self.window_size = window_size
        self.history = deque(maxlen=window_size)
        
    def process(self, audio):
        self.history.append(np.median(np.abs(audio)))
        if len(self.history) < self.window_size:
            return audio
        
        median = np.median(list(self.history))
        threshold = median * self.threshold_factor
        
        output = np.clip(audio, -threshold, threshold)
        return output

class AIDenoiser:
    """Facebook Denoiser wrapper"""
    def __init__(self, model_path='models/current/best.th'):
        print(f"Loading AI model from {model_path}...")
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        model_class = checkpoint['class']
        self.model = model_class(*checkpoint['args'], **checkpoint['kwargs'])
        self.model.load_state_dict(checkpoint['state'])
        self.model.eval()
        print("✅ AI model ready")
        
    def process(self, audio):
        x = torch.from_numpy(audio).float().unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            y = self.model(x)
        return y.squeeze().cpu().numpy()

class SoftLimiter:
    """Prevent clipping with soft limiting"""
    def __init__(self, threshold=0.95):
        self.threshold = threshold
        
    def process(self, audio):
        scale = self.threshold
        output = np.where(
            np.abs(audio) > self.threshold,
            scale * np.tanh(audio / scale),
            audio
        )
        return output

class FilterChain:
    """Coordinate all filter stages"""
    def __init__(self, config, sr=16000):
        self.filters = []
        
        if config['filters']['highpass']['enabled']:
            hpf = HighPassFilter(
                cutoff=config['filters']['highpass']['cutoff_freq'],
                order=config['filters']['highpass']['order'],
                sr=sr
            )
            self.filters.append(('HPF', hpf))
            print("✅ Filter 1: High-Pass Filter")
        
        if config['filters']['impulse_suppressor']['enabled']:
            ins = ImpulseNoiseSuppressor(
                threshold_factor=config['filters']['impulse_suppressor']['threshold_factor'],
                window_size=config['filters']['impulse_suppressor']['window_size']
            )
            self.filters.append(('ImpulseSuppressor', ins))
            print("✅ Filter 2: Impulse Noise Suppressor")
        
        if config['filters']['ai_denoiser']['enabled']:
            model_path = config['filters']['ai_denoiser']['model_path']
            if model_path is None:
                model_path = 'models/current/best.th'
            denoiser = AIDenoiser(model_path)
            self.filters.append(('AIDenoiser', denoiser))
            print("✅ Filter 3: AI Denoiser")
        
        if config['filters']['limiter']['enabled']:
            limiter = SoftLimiter(
                threshold=config['filters']['limiter']['threshold']
            )
            self.filters.append(('SoftLimiter', limiter))
            print("✅ Filter 4: Soft Limiter")
    
    def process(self, audio):
        for name, filter_obj in self.filters:
            audio = filter_obj.process(audio)
        return audio

# ========== Main Processing ==========

def process_wav(input_path, output_path, config_path=None):
    """Process .wav file through filter chain"""
    
    # Load config
    if config_path is None:
        config_path = Path(__file__).parent / 'audio_pipeline' / 'configs' / 'filter_chain_optimized.yaml'
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    print("="*60)
    print(f"📄 Input: {input_path}")
    print(f"📄 Output: {output_path}")
    print(f"📄 Config: {Path(config_path).name}")
    print("="*60 + "\n")
    
    # Read input audio
    print("📥 Reading input file...")
    sr_original, audio = wavfile.read(input_path)
    
    # Convert to mono if stereo
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
        print(f"   Converted stereo to mono")
    
    # Normalize to float32 [-1, 1]
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    elif audio.dtype == np.int32:
        audio = audio.astype(np.float32) / 2147483648.0
    
    print(f"   Sample rate: {sr_original} Hz")
    print(f"   Duration: {len(audio)/sr_original:.2f} seconds")
    print(f"   Samples: {len(audio):,}")
    
    # Resample to 16kHz if needed
    target_sr = config['audio']['sample_rate']
    if sr_original != target_sr:
        print(f"\n🔄 Resampling: {sr_original} Hz → {target_sr} Hz...")
        audio = signal.resample_poly(audio, target_sr, sr_original)
    
    # Initialize filter chain
    print("\n🎛️  Initializing filter chain...")
    filter_chain = FilterChain(config, sr=target_sr)
    
    # Process audio
    print(f"\n🚀 Processing audio...")
    processed = filter_chain.process(audio)
    
    # Resample back to original sample rate
    if sr_original != target_sr:
        print(f"🔄 Resampling back: {target_sr} Hz → {sr_original} Hz...")
        processed = signal.resample_poly(processed, sr_original, target_sr)
    
    # Normalize and convert back to int16
    print("💾 Saving output file...")
    processed = np.clip(processed, -1.0, 1.0)  # Clip to valid range
    processed = (processed * 32767).astype(np.int16)
    
    # Save output
    wavfile.write(output_path, sr_original, processed)
    
    print("\n" + "="*60)
    print(f"✅ Processing complete!")
    print(f"📁 Output saved: {output_path}")
    print("="*60 + "\n")

# ========== CLI ==========

def main():
    parser = argparse.ArgumentParser(
        description='Process .wav file through audio filter chain',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default config (optimized)
  python process_audio.py gunshot.wav gunshot_denoised.wav
  
  # Use custom config
  python process_audio.py input.wav output.wav --config filter_chain_simple.yaml
  
  # Use AI denoiser only
  python process_audio.py input.wav output.wav --config audio_pipeline/configs/filter_chain_test1_ai_only.yaml
        """
    )
    
    parser.add_argument('input', type=str, help='Input .wav file')
    parser.add_argument('output', type=str, help='Output .wav file')
    parser.add_argument('--config', type=str, default=None,
                        help='Config file path (default: filter_chain_optimized.yaml)')
    
    args = parser.parse_args()
    
    # Check input file exists
    if not Path(args.input).exists():
        print(f"❌ Error: Input file not found: {args.input}")
        return
    
    # Process
    try:
        process_wav(args.input, args.output, args.config)
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
