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
    """Remove low-frequency rumble (<300Hz for voice preservation)"""
    def __init__(self, cutoff=300, order=4, sr=16000):
        self.sos = signal.butter(order, cutoff, 'hp', fs=sr, output='sos')
        self.zi = signal.sosfilt_zi(self.sos)
        
    def process(self, audio):
        filtered, self.zi = signal.sosfilt(self.sos, audio, zi=self.zi)
        return filtered

class LowPassFilter:
    """Remove high-frequency gunfire cracks (>3400Hz)"""
    def __init__(self, cutoff=3400, order=4, sr=16000):
        self.sos = signal.butter(order, cutoff, 'lp', fs=sr, output='sos')
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

class GunfireSuppressor:
    """
    Detect and suppress gunfire based on duration + amplitude
    
    Strategy:
    - Detect SHORT (< 20ms) + HIGH AMPLITUDE signals
    - Apply aggressive suppression ONLY to those segments
    - Leave continuous voice untouched
    """
    def __init__(self, 
                 impulse_threshold=5.0,    # Amplitude threshold (x RMS)
                 impulse_duration_ms=20,   # Max impulse duration
                 suppression_gain=0.1,     # Gain for detected impulses (0.1 = 90% reduction)
                 attack_ms=1,              # Attack time
                 release_ms=50,            # Release time
                 sr=16000):
        
        self.impulse_threshold = impulse_threshold
        self.impulse_duration_samples = int(impulse_duration_ms * sr / 1000)
        self.suppression_gain = suppression_gain
        self.attack_samples = int(attack_ms * sr / 1000)
        self.release_samples = int(release_ms * sr / 1000)
        self.sr = sr
        
        # State
        self.rms_history = deque(maxlen=100)
        
    def detect_impulses(self, audio):
        """
        Detect short-duration, high-amplitude segments
        Returns: binary mask (1 = impulse, 0 = voice)
        """
        # Calculate RMS with sliding window
        window = 400  # 25ms @ 16kHz
        audio_squared = audio ** 2
        rms = np.sqrt(np.convolve(audio_squared, np.ones(window)/window, mode='same'))
        
        # Update running RMS (for adaptive threshold)
        current_rms = np.mean(rms)
        self.rms_history.append(current_rms)
        avg_rms = np.mean(list(self.rms_history))
        
        # Threshold for impulse detection
        threshold = avg_rms * self.impulse_threshold
        
        # Detect high-amplitude samples
        high_amplitude = np.abs(audio) > threshold
        
        # Check duration: impulses are SHORT
        mask = np.zeros_like(audio, dtype=bool)
        
        in_impulse = False
        impulse_start = 0
        
        for i, is_high in enumerate(high_amplitude):
            if is_high and not in_impulse:
                in_impulse = True
                impulse_start = i
                
            elif not is_high and in_impulse:
                impulse_length = i - impulse_start
                
                # If SHORT enough, mark as gunfire
                if impulse_length < self.impulse_duration_samples:
                    mask[impulse_start:i] = True
                
                in_impulse = False
        
        # Apply smooth envelope to mask
        mask = self._apply_envelope(mask.astype(float))
        
        return mask
    
    def _apply_envelope(self, mask):
        """Apply smooth attack/release to mask"""
        if self.attack_samples < 1:
            self.attack_samples = 1
        if self.release_samples < 1:
            self.release_samples = 1
            
        envelope = np.concatenate([
            np.linspace(0, 1, self.attack_samples),
            np.ones(10),
            np.linspace(1, 0, self.release_samples)
        ])
        
        if len(envelope) > 0:
            envelope = envelope / np.sum(envelope)
            smoothed = np.convolve(mask, envelope, mode='same')
        else:
            smoothed = mask
            
        return np.clip(smoothed, 0, 1)
    
    def process(self, audio):
        """
        Suppress gunfire while preserving voice
        """
        # Detect impulses
        impulse_mask = self.detect_impulses(audio)
        
        # Apply suppression ONLY to impulse regions
        # impulse_mask: 1 = gunfire (suppress), 0 = voice (preserve)
        gain = 1.0 - impulse_mask * (1.0 - self.suppression_gain)
        
        output = audio * gain
        
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
        
        # Add low-pass filter if configured
        if 'lowpass' in config['filters'] and config['filters']['lowpass']['enabled']:
            lpf = LowPassFilter(
                cutoff=config['filters']['lowpass']['cutoff_freq'],
                order=config['filters']['lowpass']['order'],
                sr=sr
            )
            self.filters.append(('LPF', lpf))
            print("✅ Filter 2: Low-Pass Filter")
        
        # Add gunfire suppressor if configured
        if 'gunfire_suppressor' in config['filters'] and config['filters']['gunfire_suppressor']['enabled']:
            gfs = GunfireSuppressor(
                impulse_threshold=config['filters']['gunfire_suppressor']['impulse_threshold'],
                impulse_duration_ms=config['filters']['gunfire_suppressor']['impulse_duration_ms'],
                suppression_gain=config['filters']['gunfire_suppressor']['suppression_gain'],
                attack_ms=config['filters']['gunfire_suppressor']['attack_ms'],
                release_ms=config['filters']['gunfire_suppressor']['release_ms'],
                sr=sr
            )
            self.filters.append(('GunfireSuppressor', gfs))
            print("✅ Filter: Gunfire Suppressor")
        
        if config['filters']['impulse_suppressor']['enabled']:
            ins = ImpulseNoiseSuppressor(
                threshold_factor=config['filters']['impulse_suppressor']['threshold_factor'],
                window_size=config['filters']['impulse_suppressor']['window_size']
            )
            self.filters.append(('ImpulseSuppressor', ins))
            print("✅ Filter 3: Impulse Noise Suppressor")
        
        if config['filters']['ai_denoiser']['enabled']:
            model_path = config['filters']['ai_denoiser']['model_path']
            if model_path is None:
                model_path = 'models/current/best.th'
            denoiser = AIDenoiser(model_path)
            self.filters.append(('AIDenoiser', denoiser))
            print("✅ Filter 4: AI Denoiser")
        
        if config['filters']['limiter']['enabled']:
            limiter = SoftLimiter(
                threshold=config['filters']['limiter']['threshold']
            )
            self.filters.append(('SoftLimiter', limiter))
            print("✅ Filter 5: Soft Limiter")
    
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
