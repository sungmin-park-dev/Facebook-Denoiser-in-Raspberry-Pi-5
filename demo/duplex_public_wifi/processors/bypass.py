"""
Bypass Processor

No audio processing - direct passthrough
"""

import numpy as np
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from demo.duplex.core.audio_processor import AudioProcessor


class BypassProcessor(AudioProcessor):
    """
    Bypass processor - no processing
    
    Simply returns input audio unchanged
    Useful for:
    - Testing raw communication quality
    - Comparing against processed audio
    - Low-latency mode
    """
    
    def __init__(self):
        """Initialize bypass processor"""
        pass
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Pass audio through unchanged
        
        Args:
            audio: Input audio (16kHz, mono, float32)
        
        Returns:
            Same audio (no modification)
        """
        return audio
    
    def get_name(self) -> str:
        """Get processor name"""
        return "Bypass (No Processing)"
    
    def get_stats(self) -> dict:
        """Get stats"""
        return {
            'type': 'bypass',
            'latency_ms': 0
        }
