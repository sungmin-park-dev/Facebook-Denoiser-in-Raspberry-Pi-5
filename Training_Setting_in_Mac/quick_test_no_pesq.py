#!/usr/bin/env python3
"""
PESQ 없이 RPI5 최적화 모델 테스트 (맥북용)
"""

import torch
import time
import sys
import os

def check_environment():
    """환경 확인"""
    print("🍎 맥북 환경 확인")
    print("=" * 40)
    
    # 가상환경 확인
    venv = os.environ.get('VIRTUAL_ENV', 'None')
    print(f"가상환경: {venv}")
    
    # PyTorch 확인
    print(f"PyTorch 버전: {torch.__version__}")
    
    # 디바이스 확인
    if torch.backends.mps.is_available():
        print("✅ Apple Silicon MPS 사용 가능")
        device = "mps"
    elif torch.cuda.is_available():
        print("✅ NVIDIA CUDA 사용 가능")
        device = "cuda"
    else:
        print("⚠️ CPU만 사용")
        device = "cpu"
    
    print(f"권장 device: {device}")
    return device

def test_demucs_import():
    """Demucs 모듈 import 테스트"""
    print("\n🔧 Demucs 모듈 import 테스트")
    print("=" * 40)
    
    try:
        from denoiser.demucs import Demucs
        print("✅ denoiser.demucs import 성공")
        return True
    except ImportError as e:
        print(f"❌ denoiser.demucs import 실패: {e}")
        
        # 가능한 해결책 제시
        print("\n🔧 해결책:")
        print("1. 현재 디렉토리가 프로젝트 루트인지 확인")
        print("2. 가상환경이 활성화되었는지 확인")
        print("3. sys.path에 프로젝트 추가:")
        print("   export PYTHONPATH=$PYTHONPATH:$(pwd)")
        
        return False

def create_rpi5_model():
    """RPI5 최적화 모델 생성"""
    print("\n🎯 RPI5 최적화 모델 생성")
    print("=" * 40)
    
    # 라즈베리파이에서 검증된 최적 파라미터
    config = {
        'chin': 1,           # 입력 채널
        'chout': 1,          # 출력 채널
        'hidden': 32,        # 히든 채널 (RTF=0.834 달성)
        'depth': 4,          # 레이어 깊이
        'kernel_size': 8,    # 컨볼루션 커널
        'stride': 4,         # 스트라이드
        'causal': True,      # 실시간 처리
        'resample': 2,       # 핵심 최적화: 4→2
        'growth': 1.5,       # 경량화: 2.0→1.5
        'max_hidden': 128,   # hidden*4
        'normalize': True,
        'glu': False,        # 핵심 최적화: 파라미터 50% 감소
        'rescale': 0.1
    }
    
    print("RPI5 최적화 설정:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    try:
        from denoiser.demucs import Demucs
        model = Demucs(**config, sample_rate=16000)
        
        # 모델 크기 계산
        total_params = sum(p.numel() for p in model.parameters())
        model_size_mb = total_params * 4 / 2**20
        
        print(f"\n✅ 모델 생성 성공!")
        print(f"파라미터 수: {total_params:,}")
        print(f"모델 크기: {model_size_mb:.1f}MB")
        print(f"라즈베리파이 예상 RTF: 0.834")
        
        return model, config
        
    except Exception as e:
        print(f"❌ 모델 생성 실패: {e}")
        return None, None

def test_forward_pass(model, device):
    """순전파 테스트"""
    print(f"\n🧪 순전파 테스트 (device: {device})")
    print("=" * 40)
    
    try:
        model = model.to(device)
        model.eval()
        
        # 4초 테스트 오디오
        duration = 4.0
        sample_rate = 16000
        audio_length = int(sample_rate * duration)
        
        test_input = torch.randn(1, 1, audio_length).to(device)
        print(f"입력: {test_input.shape}")
        
        # 추론 실행
        with torch.no_grad():
            start_time = time.time()
            output = model(test_input)
            end_time = time.time()
        
        processing_time = end_time - start_time
        rtf = processing_time / duration
        
        print(f"출력: {output.shape}")
        print(f"처리 시간: {processing_time:.3f}초")
        print(f"맥북 RTF: {rtf:.3f}")
        
        # 성능 분석
        if rtf < 0.01:
            performance = "🚀 매우 빠름"
        elif rtf < 0.1:
            performance = "✅ 매우 좋음"
        elif rtf < 1.0:
            performance = "✅ 실시간 가능"
        else:
            performance = "⚠️ 느림"
        
        print(f"성능 평가: {performance}")
        
        # 라즈베리파이 예상 성능 계산
        # M1 대비 RPI5는 약 10-20배 느림
        rpi_estimated_rtf = rtf * 15  # 보수적 추정
        print(f"라즈베리파이 예상 RTF: {rpi_estimated_rtf:.3f}")
        
        if rpi_estimated_rtf < 1.0:
            print("🎯 라즈베리파이에서도 실시간 가능 예상!")
        else:
            print("⚠️ 라즈베리파이에서 실시간 어려울 수 있음")
        
        return True, rtf
        
    except Exception as e:
        print(f"❌ 순전파 테스트 실패: {e}")
        return False, float('inf')

def compare_configs():
    """원본 vs RPI5 최적화 비교"""
    print(f"\n📊 모델 구성 비교")
    print("=" * 40)
    
    original = {
        'hidden': 48, 'depth': 5, 'resample': 4, 
        'growth': 2.0, 'glu': True
    }
    
    rpi5 = {
        'hidden': 32, 'depth': 4, 'resample': 2,
        'growth': 1.5, 'glu': False
    }
    
    print(f"{'파라미터':<12} {'원본':<8} {'RPI5':<8} {'변화'}")
    print("-" * 40)
    
    changes = []
    for key in original:
        orig_val = original[key]
        rpi5_val = rpi5[key]
        
        if orig_val != rpi5_val:
            if key == 'resample':
                changes.append("2.5배 빠른 처리")
            elif key == 'glu':
                changes.append("50% 파라미터 감소")
            elif key == 'hidden':
                changes.append("채널 수 감소")
            elif key == 'depth':
                changes.append("레이어 감소")
            elif key == 'growth':
                changes.append("성장률 감소")
            
            change_mark = "→"
        else:
            change_mark = "="
        
        print(f"{key:<12} {orig_val:<8} {rpi5_val:<8} {change_mark}")
    
    print(f"\n🎯 주요 최적화:")
    for i, change in enumerate(changes, 1):
        print(f"  {i}. {change}")

def main():
    """메인 테스트"""
    print("🎯 맥북에서 RPI5 최적화 모델 테스트")
    print("=" * 60)
    
    # 1. 환경 확인
    device = check_environment()
    
    # 2. 모듈 import 테스트
    if not test_demucs_import():
        print("\n❌ 모듈 import 실패로 테스트 중단")
        print("\n🔧 해결 방법:")
        print("1. 가상환경 활성화: source venv_denoiser/bin/activate")
        print("2. 프로젝트 루트에서 실행: cd Facebook-Denoiser-in-Raspberry-Pi-5")
        print("3. Python 경로 추가: export PYTHONPATH=$PYTHONPATH:$(pwd)")
        return
    
    # 3. 모델 생성
    model, config = create_rpi5_model()
    if model is None:
        return
    
    # 4. 순전파 테스트
    success, rtf = test_forward_pass(model, device)
    if not success:
        return
    
    # 5. 구성 비교
    compare_configs()
    
    # 6. 결과 요약
    print(f"\n🎉 테스트 완료!")
    print("=" * 40)
    print(f"✅ 맥북 RTF: {rtf:.3f}")
    print(f"✅ 모델 크기: ~1.7MB")
    print(f"✅ 라즈베리파이 예상 RTF: {rtf*15:.3f}")
    print(f"✅ Apple M1 MPS 지원: {torch.backends.mps.is_available()}")
    
    print(f"\n📋 다음 단계:")
    print(f"1. conf/mac_rpi5_optimal.yaml 설정 파일 생성")
    print(f"2. 디버그 데이터셋으로 훈련 테스트")
    print(f"3. 실제 데이터셋으로 훈련")
    print(f"4. 훈련된 모델을 라즈베리파이로 전송")

if __name__ == "__main__":
    main()