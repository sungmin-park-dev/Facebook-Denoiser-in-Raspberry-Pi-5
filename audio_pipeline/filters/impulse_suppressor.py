"""
Impulse Noise Suppressor Module
==============================

Detects and suppresses sudden impulse noise (clicks, pops, etc.).
"""

import numpy as np


class ImpulseNoiseSuppressor:
    """Impulse noise detection and suppression using threshold-based method."""

    def __init__(self, threshold_factor=3.0, window_size=5):
        """
        Initialize impulse noise suppressor.

        Args:
            threshold_factor (float): Threshold multiplier for detection (default: 3.0)
            window_size (int): Window size for median filtering (default: 5)
        """
        self.threshold_factor = threshold_factor
        self.window_size = window_size
        self.history = np.zeros(window_size)

    def process(self, audio_chunk):
        """
        Process audio chunk to suppress impulse noise.

        Args:
            audio_chunk (np.ndarray): Input audio chunk

        Returns:
            np.ndarray: Processed audio chunk with impulse noise suppressed
        """
        output = audio_chunk.copy()

        for i, sample in enumerate(audio_chunk):
            # Calculate local statistics
            window_start = max(0, i - self.window_size // 2)
            window_end = min(len(audio_chunk), i + self.window_size // 2 + 1)
            local_window = audio_chunk[window_start:window_end]

            # Compute median and MAD (Median Absolute Deviation)
            median_val = np.median(local_window)
            mad = np.median(np.abs(local_window - median_val))

            # Detect impulse noise
            threshold = self.threshold_factor * mad
            if abs(sample - median_val) > threshold:
                # Replace with median value
                output[i] = median_val

        return output

    def reset(self):
        """Reset suppressor state."""
        self.history.fill(0)