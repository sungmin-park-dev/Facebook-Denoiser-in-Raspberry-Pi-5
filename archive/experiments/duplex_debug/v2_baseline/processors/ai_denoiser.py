"""
AI Denoiser Processor

AI-based noise reduction using Light-32-Depth4 model
"""

import numpy as np
import torch
from pathlib import Path
import sys
import warnings

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from demo.duplex.core.audio_processor import AudioProcessor
from audio_pipeline.core.model_loader import ModelLoader


class AIDenoiserProcessor(AudioProcessor):
    """
    AI-based denoising processor
    
    Uses Facebook Denoiser architecture (Light-32-Depth4)
    - Trained on Valentini dataset
    - Optimized for RP5 (RTF ~0.05 with JIT)
    - Removes background noise while preserving voice
    """
    
    def __init__(self, model_name: str = "Light-32-Depth4"):
        """
        Initialize AI denoiser
        
        Args:
            model_name: Model name to load
        """
        print(f"🤖 Loading {model_name}...")
        self.model_name = model_name
        self.denoiser = ModelLoader.load(model_name)
        self.denoiser.eval()
        
        # JIT compilation for 30% speedup
        print("⚡ JIT compiling model for faster inference...")
        dummy_input = torch.randn(1, 1, 16000)  # 1 second @ 16kHz
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with torch.no_grad():
                self.denoiser = torch.jit.trace(self.denoiser, dummy_input)
        
        print(f"✅ {model_name} loaded (JIT optimized)")
        
        # Logging
        self._log_counter = 0
    
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply AI denoising with input normalization
        
        Args:
            audio: Input audio (16kHz, mono, float32)
        
        Returns:
            Denoised audio (same format)
        """
        # Measure input level
        input_level = np.abs(audio).max()
        
        # ===== 추가: 입력 정규화 =====
        if input_level > 1e-6:
            # Normalize to peak = 1.0
            audio_normalized = audio / (input_level + 1e-8)
            audio_normalized = np.clip(audio_normalized, -1.0, 1.0)
        else:
            # Silent audio, no normalization
            audio_normalized = audio
        # ============================
        
        with torch.no_grad():
            # Convert to tensor: [batch=1, channels=1, time]
            audio_tensor = torch.from_numpy(audio_normalized).float().unsqueeze(0).unsqueeze(0)  # ← 변경!
            
            # Denoise
            denoised = self.denoiser(audio_tensor)
            
            # Convert back to numpy
            audio_denoised = denoised.squeeze().cpu().numpy()
        
        # ===== 추가: 원래 스케일로 복원 =====
        if input_level > 1e-6:
            audio_denoised = audio_denoised * input_level
        # ====================================
        
        # Measure output level
        output_level = np.abs(audio_denoised).max()
        
        # Log every 10 seconds (500 chunks @ 20ms)
        self._log_counter += 1
        if self._log_counter % 500 == 0:
            if input_level > 0.001:
                reduction = (1 - output_level / (input_level + 1e-8)) * 100
                print(f"🤖 AI Active: In={input_level:.3f} → Out={output_level:.3f} (Noise ↓{reduction:.1f}%)")
        
        return audio_denoised



    def get_name(self) -> str:
        """Get processor name"""
        return f"AI Denoiser ({self.model_name})"
    
    def get_stats(self) -> dict:
        """Get stats"""
        return {
            'type': 'ai_denoiser',
            'model': self.model_name,
            'rtf': 0.05  # Approximate (with JIT)
        }