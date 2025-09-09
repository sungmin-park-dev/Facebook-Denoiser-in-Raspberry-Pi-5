#!/usr/bin/env python3
"""
빠른 RTF 테스트 - 한 번에 하나씩 모델 테스트
"""

import torch
import time
import sys
import os

sys.path.append('/home/test1/denoiser')
from denoiser.demucs import Demucs

def quick_rtf_test(hidden=32, depth=3, resample=2):
    """빠른 RTF 테스트"""
    
    print(f"테스트 설정: hidden={hidden}, depth={depth}, resample={resample}")
    
    # CPU 성능 최적화
    torch.set_num_threads(4)
    
    config = {
        'chin': 1, 'chout': 1, 'hidden': hidden, 'depth': depth,
        'kernel_size': 8, 'stride': 4, 'causal': True,
        'resample': resample, 'growth': 1.5, 'max_hidden': hidden * 4,
        'normalize': True, 'glu': False, 'rescale': 0.1
    }
    
    try:
        model = Demucs(**config, sample_rate=16000)
        model.eval()
        
        # 모델 크기 계산
        model_size_mb = sum(p.numel() for p in model.parameters()) * 4 / 2**20
        print(f"모델 크기: {model_size_mb:.1f}MB")
        
        # 4초 오디오로 테스트
        audio_length = 16000 * 4  # 4초
        test_audio = torch.randn(1, 1, audio_length)
        
        # 워밍업
        with torch.no_grad():
            _ = model(test_audio)
        
        # 실제 측정
        start_time = time.time()
        with torch.no_grad():
            for _ in range(3):
                output = model(test_audio)
        end_time = time.time()
        
        processing_time = (end_time - start_time) / 3
        rtf = processing_time / 4.0  # 4초 오디오
        
        print(f"처리 시간: {processing_time:.3f}초")
        print(f"RTF: {rtf:.3f}")
        
        if rtf < 1.0:
            print("🎯 실시간 처리 가능!")
        else:
            print("⚠️ 실시간 처리 불가")
        
        return rtf, model_size_mb
        
    except Exception as e:
        print(f"에러: {e}")
        return float('inf'), 0

if __name__ == "__main__":
    print("라즈베리파이 5 빠른 RTF 테스트")
    print("=" * 40)
    
    # 시스템 정보
    print(f"PyTorch: {torch.__version__}")
    print(f"CPU 스레드: {torch.get_num_threads()}")
    print()
    
    # 여러 설정 테스트
    configs = [
        (16, 2, 2),   # 극경량
        (24, 3, 2),   # 초경량
        (32, 3, 2),   # 경량
        (40, 4, 2),   # 표준경량
        (48, 4, 2),   # 기본경량
    ]
    
    best_rtf = float('inf')
    best_config = None
    
    for hidden, depth, resample in configs:
        print(f"\n테스트 {len([c for c in configs if configs.index(c) <= configs.index((hidden, depth, resample))])}/{len(configs)}")
        rtf, size = quick_rtf_test(hidden, depth, resample)
        
        if rtf < best_rtf:
            best_rtf = rtf
            best_config = (hidden, depth, resample)
        
        print("-" * 30)
    
    print(f"\n최적 설정: hidden={best_config[0]}, depth={best_config[1]}, resample={best_config[2]}")
    print(f"최적 RTF: {best_rtf:.3f}")
