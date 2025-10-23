"""
AI Denoiser Module
=================

Wrapper for Facebook Denoiser integration into the audio pipeline.
"""

import torch
import numpy as np
from pathlib import Path


class AIDenoiser:
    """Facebook Denoiser wrapper for real-time processing."""

    def __init__(self, model_path=None, device='cpu'):
        """
        Initialize AI denoiser.

        Args:
            model_path (str): Path to the trained model (default: auto-detect)
            device (str): Processing device ('cpu' or 'cuda')
        """
        self.device = device

        # Auto-detect model path if not provided
        if model_path is None:
            model_path = self._find_best_model()

        self.model_path = model_path
        self.model = None
        self._load_model()

    def _find_best_model(self):
        """Find the best available model."""
        # Look for models in the models directory
        models_dir = Path(__file__).parent.parent.parent / "models"
        if models_dir.exists() and (models_dir / "best.th").exists():
            return str(models_dir / "best.th")

        # Fallback to outputs directory
        outputs_dir = Path(__file__).parent.parent.parent / "outputs"
        model_paths = list(outputs_dir.glob("**/best.th"))
        if model_paths:
            return str(model_paths[0])

        raise FileNotFoundError("No model file (best.th) found")

    def _load_model(self):
        """Load the denoiser model."""
        try:
            # Import denoiser after ensuring it's available
            import sys
            import os
            denoiser_path = Path(__file__).parent.parent.parent / "denoiser"
            sys.path.insert(0, str(denoiser_path.parent))

            from denoiser import pretrained

            # Load model
            self.model = pretrained.load_model(self.model_path)
            self.model.eval()
            self.model = self.model.to(self.device)

        except Exception as e:
            raise RuntimeError(f"Failed to load AI denoiser model: {e}")

    def process(self, audio_chunk):
        """
        Process audio chunk with AI denoiser.

        Args:
            audio_chunk (np.ndarray): Input audio chunk

        Returns:
            np.ndarray: Denoised audio chunk
        """
        if self.model is None:
            return audio_chunk

        try:
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio_chunk).float().unsqueeze(0).to(self.device)

            # Process with model
            with torch.no_grad():
                denoised = self.model(audio_tensor)

            # Convert back to numpy
            result = denoised.squeeze(0).cpu().numpy()
            return result

        except Exception as e:
            print(f"AI denoiser processing error: {e}")
            return audio_chunk

    def reset(self):
        """Reset denoiser state (if needed)."""
        # For stateless models, no reset needed
        pass