#!/usr/bin/env python3
"""
AI 기반 오디오 디노이징
- Facebook Denoiser (dns64) 사용
- Waveform domain에서 end-to-end 처리
"""

import torch
import torchaudio
from pathlib import Path
import sys

# 프로젝트 루트 경로 추가
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from denoiser import pretrained

class AIDenoiser:
    def __init__(self, model_name='dns64'):
        """
        AI 디노이저 초기화
        
        Args:
            model_name: 'dns64', 'dns48', 'master64' 중 선택
        """
        print(f"🤖 Loading {model_name} model...")
        
        if model_name == 'dns64':
            self.model = pretrained.dns64()
        elif model_name == 'dns48':
            self.model = pretrained.dns48()
        elif model_name == 'master64':
            self.model = pretrained.master64()
        else:
            raise ValueError(f"Unknown model: {model_name}")
        
        self.model.eval()
        print("✅ Model loaded")
    
    def denoise_file(self, input_path, output_path):
        """
        오디오 파일 디노이징
        
        Args:
            input_path: 노이즈 포함 오디오 경로
            output_path: 디노이징 결과 저장 경로
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        print(f"\n📂 Processing: {input_path.name}")
        
        # 오디오 로드
        wav, sr = torchaudio.load(input_path)
        print(f"   Sample rate: {sr} Hz")
        print(f"   Duration: {wav.shape[-1] / sr:.2f} sec")
        
        # 16kHz로 리샘플링 (모델 요구사항)
        if sr != 16000:
            print(f"   Resampling: {sr} Hz → 16000 Hz")
            resampler = torchaudio.transforms.Resample(sr, 16000)
            wav = resampler(wav)
            sr = 16000
        
        # 모노로 변환 (필요시)
        if wav.shape[0] > 1:
            print(f"   Converting to mono")
            wav = wav.mean(dim=0, keepdim=True)
        
        # 디노이징
        print("   🔄 Denoising...")
        with torch.no_grad():
            enhanced = self.model(wav.unsqueeze(0))  # [1, 1, samples]
            enhanced = enhanced.squeeze(0)  # [1, samples]
        
        # 저장
        output_path.parent.mkdir(parents=True, exist_ok=True)
        torchaudio.save(output_path, enhanced.cpu(), sr)
        print(f"   ✅ Saved: {output_path}")
        
        return enhanced, sr

def batch_denoise(input_dir, output_dir, model_name='dns64'):
    """
    디렉토리 내 모든 오디오 파일 디노이징
    
    Args:
        input_dir: 노이즈 오디오 디렉토리
        output_dir: 결과 저장 디렉토리
        model_name: 사용할 모델명
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
    print(f"🎵 AI-based Audio Denoising")
    print("="*60)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Model:  {model_name}")
    print(f"Files:  {len(audio_files)}")
    print("="*60)
    
    # 디노이저 초기화
    denoiser = AIDenoiser(model_name)
    
    # 배치 처리
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}]")
        
        output_file = output_dir / audio_file.name
        
        try:
            denoiser.denoise_file(audio_file, output_file)
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "="*60)
    print("🎉 Batch processing complete!")
    print("="*60)

# ==================== 메인 ====================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-based audio denoising')
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='demo/audio_comparison/samples/noisy',
        help='Input directory with noisy audio files'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='demo/audio_comparison/samples/ai',
        help='Output directory for denoised audio'
    )
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='dns64',
        choices=['dns64', 'dns48', 'master64'],
        help='Model to use (default: dns64)'
    )
    
    args = parser.parse_args()
    
    batch_denoise(args.input, args.output, args.model)