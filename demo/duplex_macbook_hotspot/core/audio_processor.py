"""
Audio Processor Base Class

Abstract interface for all audio processing modules
"""

from abc import ABC, abstractmethod
import numpy as np


class AudioProcessor(ABC):
    """
    Base class for all audio processors
    
    All processors must implement:
    - process(): Transform audio (16kHz, mono, float32 [-1, 1])
    - get_name(): Return display name
    """
    
    @abstractmethod
    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Process audio signal
        
        Args:
            audio: Input audio (16kHz, mono, float32, range: [-1.0, 1.0])
                   Shape: (n_samples,)
        
        Returns:
            Processed audio (same format as input)
        
        Note:
            - Input/output must be same length
            - Must preserve data type (float32)
            - Must maintain range [-1, 1]
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get processor name for display
        
        Returns:
            Human-readable processor name
        """
        pass
    
    def get_stats(self) -> dict:
        """
        Get processor statistics (optional)
        
        Returns:
            Dictionary with processor-specific stats
        """
        return {}
