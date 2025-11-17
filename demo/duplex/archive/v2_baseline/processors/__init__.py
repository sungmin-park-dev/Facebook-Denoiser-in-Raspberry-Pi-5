"""
Audio Processors for RP5 Full-Duplex

Available processors:
- BypassProcessor: No processing (passthrough)
- AIDenoiserProcessor: AI-based denoising
- ClassicalFiltersProcessor: Classical noise reduction (TBD)
"""

from .bypass import BypassProcessor
from .ai_denoiser import AIDenoiserProcessor
from .classical_filters import ClassicalFiltersProcessor

__all__ = [
    'BypassProcessor',
    'AIDenoiserProcessor',
    'ClassicalFiltersProcessor'
]
