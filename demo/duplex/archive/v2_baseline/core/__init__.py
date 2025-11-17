"""
Core modules for RP5 Full-Duplex Communication

- audio_comm: UDP communication, Opus codec, resampling
- audio_processor: Base class for audio processing
"""

from .audio_processor import AudioProcessor
from .audio_comm import AudioComm

__all__ = ['AudioProcessor', 'AudioComm']
