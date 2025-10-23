"""
Audio Filter Modules
===================

Individual filter implementations for the 4-stage chain:
- highpass: High-pass filter (80Hz)
- impulse_suppressor: Impulse noise suppression
- ai_denoiser: AI denoiser wrapper
- limiter: Soft limiter
"""

from .highpass import HighPassFilter
from .impulse_suppressor import ImpulseNoiseSuppressor
from .ai_denoiser import AIDenoiser
from .limiter import SoftLimiter

__all__ = [
    'HighPassFilter',
    'ImpulseNoiseSuppressor',
    'AIDenoiser',
    'SoftLimiter'
]