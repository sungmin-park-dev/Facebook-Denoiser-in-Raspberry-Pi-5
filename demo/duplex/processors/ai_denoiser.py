"""
AI Denoiser Processor

AI-based noise reduction using Light-32-Depth4 model
"""

import numpy as np
import torch
from pathlib import Path
import sys
import warnings
import time

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from demo.duplex.core.audio_processor import AudioProcessor
from audio_pipeline.core.model_loader import ModelLoader


class AIDenoiserProcessor(AudioProcessor):
    """
    AI-based denoising processor
    
    Uses Facebook Denoiser architecture (Light-32-Depth4)
    - Trained on Valentini dataset
    - Optimized for RP5 (RTF ~0.05 with JIT)
    - Removes background noise while preserving voice
    """
    
    def __init__(self, model_name: str = "Light-32-Depth4"):
        """
        Initialize AI denoiser
        
        Args:
            model_name: Model name to load
        """
        print(f"🤖 Loading {model_name}...")
        self.model_name = model_name
        self.denoiser = ModelLoader.load(model_name)
        self.denoiser.eval()
        
        # JIT compilation for 30% speedup
        print("⚡ JIT compiling model for faster inference...")
        dummy_input = torch.randn(1, 1, 16000)  # 1 second @ 16kHz
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with torch.no_grad():
                self.denoiser = torch.jit.trace(self.denoiser, dummy_input)
        
        print(f"✅ {model_name} loaded (JIT optimized)")
        
        # Logging
        self._log_counter = 0
        
        # ===== RTF 측정용 =====
        self._rtf_samples = []
        self._rtf_log_interval = 50  # 50번마다 RTF 출력
        # ====================
    
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply AI denoising with input/output normalization
        
        Args:
            audio: Input audio (16kHz, mono, float32)
        
        Returns:
            Denoised audio (same format)
        """
        # ===== 시작 시간 측정 =====
        start_time = time.perf_counter()
        # ========================
        
        # Measure input level
        input_level = np.abs(audio).max()
        
        # Input normalization
        if input_level > 1e-6:
            audio_normalized = audio / (input_level + 1e-8)
            audio_normalized = np.clip(audio_normalized, -1.0, 1.0)
        else:
            audio_normalized = audio
        
        with torch.no_grad():
            # Convert to tensor: [batch=1, channels=1, time]
            audio_tensor = torch.from_numpy(audio_normalized).float().unsqueeze(0).unsqueeze(0)
            
            # AI denoising
            output_tensor = self.denoiser(audio_tensor)
            
            # Convert back to numpy
            output = output_tensor.squeeze().numpy()
        
        # ===== 출력 정규화 강화 =====
        output_level = np.abs(output).max()
        
        if output_level > 1.0:
            # 클리핑 방지: 1.0을 초과하면 스케일 다운
            output = output / (output_level + 1e-8)
            output = np.clip(output, -1.0, 1.0)
            
            # 경고 로그
            if self._log_counter % 100 == 0:
                print(f"⚠️  AI output clipping prevented: {output_level:.3f} → 1.0")
        
        # 입력 레벨 복원 (but 1.0 이하로 제한)
        if input_level > 1e-6:
            output = output * min(input_level, 0.95)  # 0.95로 제한 (여유)
        # ==========================
        
        # ===== 종료 시간 및 RTF 계산 =====
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        chunk_duration_ms = len(audio) / 16.0  # 16kHz → ms
        rtf = elapsed_ms / chunk_duration_ms
        
        self._rtf_samples.append(rtf)
        
        # RTF 통계 출력
        if self._log_counter % self._rtf_log_interval == 0 and len(self._rtf_samples) > 0:
            avg_rtf = np.mean(self._rtf_samples)
            max_rtf = np.max(self._rtf_samples)
            min_rtf = np.min(self._rtf_samples)
            print(f"🤖 AI RTF: avg={avg_rtf:.3f}, max={max_rtf:.3f}, min={min_rtf:.3f} | "
                  f"Process time: {elapsed_ms:.1f}ms / {chunk_duration_ms:.1f}ms")
            self._rtf_samples = []  # 리셋
        # ================================
        
        self._log_counter += 1
        return output.astype(np.float32)
    
    
    def get_name(self) -> str:
        """Return processor name"""
        return f"AI Denoiser ({self.model_name})"
