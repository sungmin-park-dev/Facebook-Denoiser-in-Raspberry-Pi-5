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
        
        # ===== 텐서 재사용 (메모리 프리할당) =====
        self.max_length = 960  # 60ms @ 16kHz
        self.input_tensor = torch.zeros(1, 1, self.max_length, dtype=torch.float32)
        self.output_buffer = np.zeros(self.max_length, dtype=np.float32)
        print(f"⚡ Pre-allocated tensors for {self.max_length} samples")
        # ========================================
        
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
        
        # ===== 입력 레벨 측정 =====
        input_peak = np.abs(audio).max()
        input_rms = np.sqrt(np.mean(audio**2))
        # ==========================
        
        # Input normalization
        if input_peak > 1e-6:
            audio_normalized = audio / (input_peak + 1e-8)
            audio_normalized = np.clip(audio_normalized, -1.0, 1.0)
        else:
            audio_normalized = audio
        
        # ===== 텐서 재사용 (메모리 복사 최소화) =====
        audio_length = len(audio_normalized)
        
        # 길이가 max_length 이하인 경우만 재사용
        if audio_length <= self.max_length:
            # 기존 텐서에 데이터 복사 (새로 생성하지 않음)
            self.input_tensor[0, 0, :audio_length] = torch.from_numpy(audio_normalized)
            if audio_length < self.max_length:
                self.input_tensor[0, 0, audio_length:] = 0  # Zero padding
            
            input_tensor = self.input_tensor[:, :, :audio_length]
        else:
            # 예외: 길이가 초과하면 새로 생성
            input_tensor = torch.from_numpy(audio_normalized).float().unsqueeze(0).unsqueeze(0)
        # ===========================================
        
        with torch.no_grad():
            # AI denoising
            output_tensor = self.denoiser(input_tensor)
            
            # ===== 출력 버퍼 재사용 =====
            output_np = output_tensor.squeeze().numpy()
            output_length = len(output_np)
            
            if output_length <= self.max_length:
                # 기존 버퍼에 복사
                self.output_buffer[:output_length] = output_np
                output = self.output_buffer[:output_length].copy()
            else:
                # 예외: 길이 초과
                output = output_np
            # ===========================
        
        # ===== 출력 정규화 강화 =====
        output_peak = np.abs(output).max()
        output_rms = np.sqrt(np.mean(output**2))
        
        if output_peak > 1.0:
            # 클리핑 방지: 1.0을 초과하면 스케일 다운
            output = output / (output_peak + 1e-8)
            output = np.clip(output, -1.0, 1.0)
            
            # 경고 로그
            if self._log_counter % 100 == 0:
                print(f"⚠️  AI output clipping prevented: {output_peak:.3f} → 1.0")
        
        # ===== 입력 레벨 복원 (증폭 강화) =====
        if input_peak > 1e-6:
            # 0.95 → 1.05 (약 10% 증폭)
            output = output * min(input_peak * 1.05, 1.0)
        # ====================================
        
        # ===== 소음 감쇠량 계산 =====
        output_rms_final = np.sqrt(np.mean(output**2))
        
        if input_rms > 1e-6 and output_rms_final > 1e-6:
            reduction_db = 20 * np.log10(input_rms / output_rms_final)
        else:
            reduction_db = 0.0
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
                  f"Process: {elapsed_ms:.1f}ms/{chunk_duration_ms:.1f}ms | "
                  f"Noise reduction: {reduction_db:.1f}dB | "
                  f"RMS: {input_rms:.4f}→{output_rms_final:.4f}")
            self._rtf_samples = []  # 리셋
        # ================================
        
        self._log_counter += 1
        return output.astype(np.float32)
    
    
    def get_name(self) -> str:
        """Return processor name"""
        return f"AI Denoiser ({self.model_name})"
