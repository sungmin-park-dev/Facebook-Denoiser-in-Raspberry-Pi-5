"""
AI Denoiser Processor

AI-based noise reduction using Light-32-Depth4 model
"""

import numpy as np
import torch
from pathlib import Path
import sys

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
    - Optimized for RP5 (RTF ~0.07)
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
        print(f"✅ {model_name} loaded")
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply AI denoising
        
        Args:
            audio: Input audio (16kHz, mono, float32)
        
        Returns:
            Denoised audio (same format)
        """
        with torch.no_grad():
            # Convert to tensor: [batch=1, channels=1, time]
            audio_tensor = torch.from_numpy(audio).float().unsqueeze(0).unsqueeze(0)
            
            # Denoise
            denoised = self.denoiser(audio_tensor)
            
            # Convert back to numpy
            audio_denoised = denoised.squeeze().cpu().numpy()
            
            return audio_denoised
    
    def get_name(self) -> str:
        """Get processor name"""
        return f"AI Denoiser ({self.model_name})"
    
    def get_stats(self) -> dict:
        """Get stats"""
        return {
            'type': 'ai_denoiser',
            'model': self.model_name,
            'rtf': 0.07  # Approximate
        }
