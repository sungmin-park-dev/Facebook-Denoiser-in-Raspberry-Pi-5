#!/usr/bin/env python3
"""
고전 음성학 기반 오디오 디노이징
- Spectral Subtraction (후처리 포함)
- Wiener Filter  
- Noise Gate
- 표준 파이프라인: 전처리 → 디노이징 → 후처리
"""

import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from scipy import signal
from scipy.ndimage import median_filter as ndimage_median_filter
from scipy.signal import medfilt

class ClassicalDenoiser:
    def __init__(self, method='spectral_subtraction', apply_bandpass=True, 
                 apply_postprocess=True):
        """
        고전 디노이저 초기화
        
        Args:
            method: 'spectral_subtraction', 'wiener', 'noise_gate' 중 선택
            apply_bandpass: 음성 대역 필터 적용 여부 (전처리)
            apply_postprocess: 후처리 적용 여부 (musical noise 완화)
        """
        self.method = method
        self.apply_bandpass = apply_bandpass
        self.apply_postprocess = apply_postprocess
        
        print(f"📚 Using classical method: {method}")
        if apply_bandpass:
            print(f"🎛️  Band-pass filter: ON (80-7600 Hz)")
        if apply_postprocess:
            print(f"✨ Post-processing: ON (musical noise reduction)")
    
    def bandpass_filter(self, audio, sr, lowcut=80, highcut=None, order=5):
        """
        음성 대역 Band-pass filter (전처리)
        
        Args:
            audio: 입력 오디오
            sr: 샘플링 레이트
            lowcut: 저주파 컷오프 (기본: 80 Hz)
            highcut: 고주파 컷오프 (None이면 자동 조정)
            order: 필터 차수
        
        Returns:
            필터링된 오디오
        """
        nyquist = sr / 2
        
        # highcut 자동 조정 (Nyquist 주파수 고려)
        if highcut is None:
            highcut = min(8000, nyquist * 0.95)
        elif highcut >= nyquist:
            highcut = nyquist * 0.95
            print(f"   ⚠️  highcut adjusted to {highcut:.0f} Hz (Nyquist limit)")
        
        low = lowcut / nyquist
        high = highcut / nyquist
        
        # 범위 검증
        if not (0 < low < 1 and 0 < high < 1 and low < high):
            raise ValueError(f"Invalid filter range: {lowcut}-{highcut} Hz for sr={sr}")
        
        # Butterworth band-pass filter (음성학 표준)
        sos = signal.butter(order, [low, high], btype='band', output='sos')
        filtered = signal.sosfilt(sos, audio)
        
        return filtered
    
    def pre_emphasis(self, audio, coef=0.97):
        """
        Pre-emphasis filter (선택적 전처리)
        - 고주파 성분 강조 (음성학 표준 전처리)
        
        Args:
            audio: 입력 오디오
            coef: pre-emphasis 계수 (기본: 0.97)
        
        Returns:
            pre-emphasized 오디오
        """
        return np.append(audio[0], audio[1:] - coef * audio[:-1])
    
    def smooth_spectrum(self, magnitude, time_window=2, freq_window=2):
        """
        시간-주파수 스무딩 (musical noise 완화)
        
        Args:
            magnitude: 스펙트럼 크기 [freq_bins, time_frames]
            time_window: 시간축 윈도우 크기
            freq_window: 주파수축 윈도우 크기
        
        Returns:
            스무딩된 스펙트럼
        """
        # 2D median filter가 musical noise에 효과적
        # size = (주파수축, 시간축)
        smoothed = ndimage_median_filter(magnitude, size=(freq_window, time_window))
        return smoothed
    
    def post_process(self, audio, sr):
        """
        후처리 (musical noise 추가 제거)
        
        Args:
            audio: 디노이징된 오디오
            sr: 샘플링 레이트
        
        Returns:
            후처리된 오디오
        """
        # Median filter 제거 (음성 보존 위해)
        audio_filtered = audio
        
        # 부드러운 low-pass만 적용
        nyquist = sr / 2
        cutoff = min(7800, nyquist * 0.97)
        
        try:
            sos = signal.butter(2, cutoff / nyquist, btype='low', output='sos')
            audio_filtered = signal.sosfilt(sos, audio_filtered)
        except Exception as e:
            print(f"   ⚠️  Post-processing low-pass skipped: {e}")
        
        return audio_filtered
    
    def spectral_subtraction(self, noisy, sr, noise_factor=1.5, floor=0.002):
        """
        Spectral Subtraction 방법 (후처리 통합)
        - 기반: Boll (1979), Berouti et al. (1979)
        - noise_factor: 노이즈 차감 강도 (표준: 1.5)
        - floor: spectral floor (표준: 0.002, -27dB)
        - 후처리: 스펙트럼 스무딩 + 시간 도메인 필터링
        """
        # STFT
        D = librosa.stft(noisy)
        magnitude = np.abs(D)
        phase = np.angle(D)
        
        # 노이즈 추정
        noise_frames = int(0.5 * sr / 512)
        noise_mag = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
        
        # Spectral Subtraction with spectral floor
        cleaned_mag = magnitude - noise_factor * noise_mag
        cleaned_mag = np.maximum(cleaned_mag, floor * magnitude)
        
        # 스펙트럼 스무딩 (2x2)
        if self.apply_postprocess:
            cleaned_mag = self.smooth_spectrum(cleaned_mag, time_window=2, freq_window=2)
        
        # ISTFT
        cleaned_D = cleaned_mag * np.exp(1j * phase)
        cleaned = librosa.istft(cleaned_D)
        
        # 시간 도메인 후처리
        if self.apply_postprocess:
            cleaned = self.post_process(cleaned, sr)
        
        return cleaned
    
    def wiener_filter(self, noisy, sr, noise_reduction=0.5):
        """
        Wiener Filter 방법 (후처리 통합)
        - 최소 평균 제곱 오차(MMSE) 기반
        - 단점: 음성과 노이즈 주파수 겹칠 때 성능 저하
        """
        # STFT
        D = librosa.stft(noisy)
        magnitude = np.abs(D)
        phase = np.angle(D)
        
        # 노이즈 파워 추정
        noise_frames = int(0.5 * sr / 512)
        noise_power = np.mean(magnitude[:, :noise_frames] ** 2, axis=1, keepdims=True)
        
        # Wiener gain 계산
        signal_power = magnitude ** 2
        wiener_gain = np.maximum(
            1 - noise_reduction * (noise_power / (signal_power + 1e-10)),
            0.0
        )
        
        # 필터 적용
        cleaned_mag = magnitude * wiener_gain
        
        # ✨ 후처리 1: 스펙트럼 스무딩
        if self.apply_postprocess:
            cleaned_mag = self.smooth_spectrum(cleaned_mag, time_window=3, freq_window=3)
        
        # ISTFT
        cleaned_D = cleaned_mag * np.exp(1j * phase)
        cleaned = librosa.istft(cleaned_D)
        
        # ✨ 후처리 2: 시간 도메인 처리
        if self.apply_postprocess:
            cleaned = self.post_process(cleaned, sr)
        
        return cleaned
    
    def noise_gate(self, noisy, sr, threshold_db=-40, ratio=10):
        """
        Noise Gate 방법 (후처리 통합)
        - 임계값 이하 신호 억제
        - 단점: 급격한 음성 변화(총성 등)에서 음성 손실
        """
        # 에너지 계산
        frame_length = 2048
        hop_length = 512
        
        # STFT
        D = librosa.stft(noisy, n_fft=frame_length, hop_length=hop_length)
        magnitude = np.abs(D)
        phase = np.angle(D)
        
        # dB로 변환
        magnitude_db = librosa.amplitude_to_db(magnitude, ref=np.max)
        
        # 게이트 적용
        mask = np.where(magnitude_db > threshold_db, 1.0, 1.0 / ratio)
        cleaned_mag = magnitude * mask
        
        # ✨ 후처리 1: 스펙트럼 스무딩
        if self.apply_postprocess:
            cleaned_mag = self.smooth_spectrum(cleaned_mag, time_window=3, freq_window=3)
        
        # ISTFT
        cleaned_D = cleaned_mag * np.exp(1j * phase)
        cleaned = librosa.istft(cleaned_D, hop_length=hop_length)
        
        # ✨ 후처리 2: 시간 도메인 처리
        if self.apply_postprocess:
            cleaned = self.post_process(cleaned, sr)
        
        return cleaned
    
    def denoise_file(self, input_path, output_path):
        """
        오디오 파일 디노이징 (전체 파이프라인)
        
        Pipeline:
        1. 로드
        2. 전처리 (DC 제거, Band-pass)
        3. 디노이징 (Spectral/Wiener/Gate + 내부 후처리)
        4. 저장
        
        Args:
            input_path: 노이즈 포함 오디오 경로
            output_path: 디노이징 결과 저장 경로
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        print(f"\n📂 Processing: {input_path.name}")
        
        # 1. 오디오 로드
        noisy, sr = librosa.load(input_path, sr=None)
        print(f"   Sample rate: {sr} Hz")
        print(f"   Duration: {len(noisy) / sr:.2f} sec")
        
        # 2. 전처리
        # 2-1. DC offset 제거
        noisy = noisy - np.mean(noisy)
        
        # 2-2. Band-pass filter (음성 대역)
        if self.apply_bandpass:
            print(f"   🎛️  Applying band-pass filter...")
            noisy = self.bandpass_filter(noisy, sr)
        
        # 2-3. Pre-emphasis (선택적, 현재 비활성화)
        # noisy = self.pre_emphasis(noisy)
        
        # 3. 디노이징 (후처리 내장)
        print(f"   🔄 Denoising with {self.method}...")
        
        if self.method == 'spectral_subtraction':
            cleaned = self.spectral_subtraction(noisy, sr)
        elif self.method == 'wiener':
            cleaned = self.wiener_filter(noisy, sr)
        elif self.method == 'noise_gate':
            cleaned = self.noise_gate(noisy, sr)
        else:
            raise ValueError(f"Unknown method: {self.method}")
        
        # 4. 길이 맞추기
        if len(cleaned) > len(noisy):
            cleaned = cleaned[:len(noisy)]
        elif len(cleaned) < len(noisy):
            cleaned = np.pad(cleaned, (0, len(noisy) - len(cleaned)))
        
        # 5. 저장
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, cleaned, sr)
        print(f"   ✅ Saved: {output_path}")
        
        return cleaned, sr

def batch_denoise(input_dir, output_dir, method='spectral_subtraction', 
                  apply_bandpass=True, apply_postprocess=True):
    """
    디렉토리 내 모든 오디오 파일 디노이징
    
    Args:
        input_dir: 노이즈 오디오 디렉토리
        output_dir: 결과 저장 디렉토리
        method: 사용할 방법
        apply_bandpass: 음성 대역 필터 적용 여부
        apply_postprocess: 후처리 적용 여부
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    
    # 지원 포맷
    audio_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    
    # 파일 목록
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(input_dir.glob(f'*{ext}'))
    
    if not audio_files:
        print(f"⚠️  No audio files found in {input_dir}")
        return
    
    print("="*60)
    print(f"📚 Classical Audio Denoising")
    print("="*60)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Method: {method}")
    print(f"Band-pass: {'ON (80-7600 Hz)' if apply_bandpass else 'OFF'}")
    print(f"Post-proc: {'ON (musical noise reduction)' if apply_postprocess else 'OFF'}")
    print(f"Files:  {len(audio_files)}")
    print("="*60)
    
    # 디노이저 초기화
    denoiser = ClassicalDenoiser(method, apply_bandpass, apply_postprocess)
    
    # 배치 처리
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}]")
        
        output_file = output_dir / audio_file.name
        
        try:
            denoiser.denoise_file(audio_file, output_file)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("🎉 Batch processing complete!")
    print("="*60)

# ==================== 메인 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Classical audio denoising')
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='demo/audio_comparison/samples/noisy',
        help='Input directory with noisy audio files'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='demo/audio_comparison/samples/classical',
        help='Output directory for denoised audio'
    )
    parser.add_argument(
        '--method', '-m',
        type=str,
        default='spectral_subtraction',
        choices=['spectral_subtraction', 'wiener', 'noise_gate'],
        help='Denoising method (default: spectral_subtraction)'
    )
    parser.add_argument(
        '--no-bandpass',
        action='store_true',
        help='Disable band-pass filter (not recommended)'
    )
    parser.add_argument(
        '--no-postprocess',
        action='store_true',
        help='Disable post-processing (for comparison)'
    )
    
    args = parser.parse_args()
    
    batch_denoise(
        args.input, 
        args.output, 
        args.method, 
        not args.no_bandpass,
        not args.no_postprocess
    )