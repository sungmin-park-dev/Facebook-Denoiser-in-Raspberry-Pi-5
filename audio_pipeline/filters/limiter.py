"""
Soft Limiter Module
==================

Prevents audio clipping with soft compression/limiting.
"""

import numpy as np


class SoftLimiter:
    """Soft limiter to prevent audio clipping."""

    def __init__(self, threshold=0.8, ratio=10.0, attack_time=0.001, release_time=0.01, sample_rate=16000):
        """
        Initialize soft limiter.

        Args:
            threshold (float): Limiting threshold (0.0-1.0, default: 0.8)
            ratio (float): Compression ratio (default: 10.0 for limiting)
            attack_time (float): Attack time in seconds (default: 0.001)
            release_time (float): Release time in seconds (default: 0.01)
            sample_rate (int): Sample rate in Hz (default: 16000)
        """
        self.threshold = threshold
        self.ratio = ratio
        self.sample_rate = sample_rate

        # Convert times to samples
        self.attack_samples = int(attack_time * sample_rate)
        self.release_samples = int(release_time * sample_rate)

        # Initialize envelope follower state
        self.envelope = 0.0

        # Pre-compute coefficients
        self.attack_coeff = np.exp(-1.0 / self.attack_samples) if self.attack_samples > 0 else 0.0
        self.release_coeff = np.exp(-1.0 / self.release_samples) if self.release_samples > 0 else 0.0

    def _soft_knee(self, x):
        """Apply soft knee compression curve."""
        if abs(x) <= self.threshold:
            return x

        # Soft compression above threshold
        sign = np.sign(x)
        abs_x = abs(x)

        # Compression ratio calculation
        over_threshold = abs_x - self.threshold
        compressed = self.threshold + over_threshold / self.ratio

        return sign * compressed

    def process(self, audio_chunk):
        """
        Process audio chunk with soft limiting.

        Args:
            audio_chunk (np.ndarray): Input audio chunk

        Returns:
            np.ndarray: Limited audio chunk
        """
        output = np.zeros_like(audio_chunk)

        for i, sample in enumerate(audio_chunk):
            # Envelope follower
            abs_sample = abs(sample)
            if abs_sample > self.envelope:
                # Attack
                self.envelope = abs_sample + (self.envelope - abs_sample) * self.attack_coeff
            else:
                # Release
                self.envelope = abs_sample + (self.envelope - abs_sample) * self.release_coeff

            # Apply soft limiting
            if self.envelope > self.threshold:
                gain_reduction = self.threshold + (self.envelope - self.threshold) / self.ratio
                gain = gain_reduction / self.envelope if self.envelope > 0 else 1.0
                output[i] = sample * gain
            else:
                output[i] = sample

        return output

    def reset(self):
        """Reset limiter state."""
        self.envelope = 0.0