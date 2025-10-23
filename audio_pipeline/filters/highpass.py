"""
High-Pass Filter Module
======================

80Hz cutoff frequency for removing low-frequency noise and rumble.
"""

import numpy as np
from scipy import signal


class HighPassFilter:
    """High-pass Butterworth filter with 80Hz cutoff."""

    def __init__(self, cutoff_freq=80, sample_rate=16000, order=4):
        """
        Initialize high-pass filter.

        Args:
            cutoff_freq (int): Cutoff frequency in Hz (default: 80)
            sample_rate (int): Sample rate in Hz (default: 16000)
            order (int): Filter order (default: 4)
        """
        self.cutoff_freq = cutoff_freq
        self.sample_rate = sample_rate
        self.order = order

        # Design Butterworth high-pass filter
        nyquist = sample_rate / 2
        normal_cutoff = cutoff_freq / nyquist
        self.b, self.a = signal.butter(order, normal_cutoff, btype='high', analog=False)

        # Initialize filter state for real-time processing
        self.zi = signal.lfilter_zi(self.b, self.a)

    def process(self, audio_chunk):
        """
        Process audio chunk with high-pass filter.

        Args:
            audio_chunk (np.ndarray): Input audio chunk

        Returns:
            np.ndarray: Filtered audio chunk
        """
        filtered, self.zi = signal.lfilter(self.b, self.a, audio_chunk, zi=self.zi)
        return filtered

    def reset(self):
        """Reset filter state."""
        self.zi = signal.lfilter_zi(self.b, self.a)