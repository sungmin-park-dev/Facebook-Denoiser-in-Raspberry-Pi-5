"""
Audio Pipeline for Real-time Audio Processing
============================================

4-stage filter chain implementation:
1. High-pass Filter (80Hz cutoff)
2. Impulse Noise Suppressor
3. AI Denoiser (Facebook Denoiser)
4. Soft Limiter

For Task A: Real-time Audio Pipeline Development
"""

__version__ = "1.0.0"
__author__ = "Audio Pipeline Team"

from .filters import *