#!/usr/bin/env python3
"""
라즈베리파이 5용 RTF 성능 테스트 스크립트
다양한 모델 구성으로 RTF를 측정하여 최적 모델을 찾습니다.
"""

import torch
import time
import sys
import os
from pathlib import Path

# denoiser 모듈 import
sys.path.append('/home/test1/denoiser')
from denoiser.demucs import Demucs, DemucsStreamer

def test_model_rtf(model_config, num_tests=5, audio_duration=4.0):
    """
    주어진 모델 구성으로 RTF를 측정합니다.
    
    Args:
        model_config (dict): 모델 설정
        num_tests (int): 테스트 반복 횟수
        audio_duration (float): 테스트 오디오 길이 (초)
    
    Returns:
        dict: RTF 결과 및 모델 정보
    """
    sample_rate = 16000
    device = 'cpu'  # 라즈베리파이는 CPU만 사용
    
    try:
        # 모델 생성
        model = Demucs(**model_config, sample_rate=sample_rate)
        model.eval()
        model_size_mb = sum(p.numel() for p in model.parameters()) * 4 / 2**20
        
        # 스트리머 생성
        streamer = DemucsStreamer(model, num_frames=1)
        
        # 테스트 오디오 생성
        audio_length = int(sample_rate * audio_duration)
        test_audio = torch.randn(1, audio_length)
        
        rtf_results = []
        
        # RTF 측정
        for test_idx in range(num_tests):
            streamer.reset_time_per_frame()
            
            # 프레임 단위로 처리
            frame_size = streamer.total_length
            audio_copy = test_audio.clone()
            
            with torch.no_grad():
                start_time = time.time()
                
                # 첫 번째 프레임
                if audio_copy.shape[1] >= frame_size:
                    streamer.feed(audio_copy[:, :frame_size])
                    audio_copy = audio_copy[:, frame_size:]
                    frame_size = streamer.stride
                
                # 나머지 프레임들
                while audio_copy.shape[1] > 0:
                    current_frame_size = min(frame_size, audio_copy.shape[1])
                    if current_frame_size > 0:
                        frame = audio_copy[:, :current_frame_size]
                        if current_frame_size < frame_size:
                            # 패딩
                            frame = torch.cat([frame, torch.zeros(1, frame_size - current_frame_size)], dim=1)
                        streamer.feed(frame)
                    audio_copy = audio_copy[:, current_frame_size:]
                
                # 마지막 처리
                streamer.flush()
                end_time = time.time()
            
            processing_time = end_time - start_time
            rtf = processing_time / audio_duration
            rtf_results.append(rtf)
        
        # 통계 계산
        avg_rtf = sum(rtf_results) / len(rtf_results)
        min_rtf = min(rtf_results)
        max_rtf = max(rtf_results)
        
        return {
            'config': model_config,
            'model_size_mb': model_size_mb,
            'avg_rtf': avg_rtf,
            'min_rtf': min_rtf,
            'max_rtf': max_rtf,
            'rtf_results': rtf_results,
            'success': True,
            'error': None
        }
        
    except Exception as e:
        return {
            'config': model_config,
            'model_size_mb': 0,
            'avg_rtf': float('inf'),
            'min_rtf': float('inf'),
            'max_rtf': float('inf'),
            'rtf_results': [],
            'success': False,
            'error': str(e)
        }

def main():
    """라즈베리파이 5용 모델 테스트 실행"""
    
    print("=" * 80)
    print("라즈베리파이 5용 실시간 음성 디노이징 모델 RTF 테스트")
    print("=" * 80)
    print(f"PyTorch 버전: {torch.__version__}")
    print(f"CPU 스레드 수: {torch.get_num_threads()}")
    print()
    
    # 테스트할 모델 구성들 (성능 우선순위 순서)
    model_configs = [
        # 1. 최경량 모델들 (RTF < 0.5 목표)
        {
            'name': 'Ultra-Light-24',
            'chin': 1, 'chout': 1, 'hidden': 24, 'depth': 3,
            'kernel_size': 8, 'stride': 4, 'causal': True,
            'resample': 2, 'growth': 1.5, 'max_hidden': 96,
            'normalize': True, 'glu': False, 'rescale': 0.1
        },
        {
            'name': 'Ultra-Light-32',
            'chin': 1, 'chout': 1, 'hidden': 32, 'depth': 3,
            'kernel_size': 8, 'stride': 4, 'causal': True,
            'resample': 2, 'growth': 1.5, 'max_hidden': 128,
            'normalize': True, 'glu': False, 'rescale': 0.1
        },
        
        # 2. 경량 모델들 (RTF < 0.8 목표)
        {
            'name': 'Light-32-Depth4',
            'chin': 1, 'chout': 1, 'hidden': 32, 'depth': 4,
            'kernel_size': 8, 'stride': 4, 'causal': True,
            'resample': 2, 'growth': 1.5, 'max_hidden': 128,
            'normalize': True, 'glu': False, 'rescale': 0.1
        },
        {
            'name': 'Light-40',
            'chin': 1, 'chout': 1, 'hidden': 40, 'depth': 4,
            'kernel_size': 8, 'stride': 4, 'causal': True,
            'resample': 2, 'growth': 1.5, 'max_hidden': 160,
            'normalize': True, 'glu': False, 'rescale': 0.1
        },
        
        # 3. 기본 경량 모델들 (RTF < 1.0 목표)
        {
            'name': 'Standard-Light-48',
            'chin': 1, 'chout': 1, 'hidden': 48, 'depth': 4,
            'kernel_size': 8, 'stride': 4, 'causal': True,
            'resample': 2, 'growth': 1.5, 'max_hidden': 192,
            'normalize': True, 'glu': False, 'rescale': 0.1
        },
        {
            'name': 'Standard-48-Resample4',
            'chin': 1, 'chout': 1, 'hidden': 48, 'depth': 4,
            'kernel_size': 8, 'stride': 4, 'causal': True,
            'resample': 4, 'growth': 1.5, 'max_hidden': 192,
            'normalize': True, 'glu': False, 'rescale': 0.1
        },
        
        # 4. 원본 경량 모델들 (비교용)
        {
            'name': 'Original-48-Depth5',
            'chin': 1, 'chout': 1, 'hidden': 48, 'depth': 5,
            'kernel_size': 8, 'stride': 4, 'causal': True,
            'resample': 4, 'growth': 2, 'max_hidden': 10000,
            'normalize': True, 'glu': True, 'rescale': 0.1
        },
        
        # 5. 더 작은 실험적 모델들
        {
            'name': 'Tiny-16',
            'chin': 1, 'chout': 1, 'hidden': 16, 'depth': 3,
            'kernel_size': 6, 'stride': 3, 'causal': True,
            'resample': 2, 'growth': 1.5, 'max_hidden': 64,
            'normalize': True, 'glu': False, 'rescale': 0.1
        },
        {
            'name': 'Micro-12',
            'chin': 1, 'chout': 1, 'hidden': 12, 'depth': 2,
            'kernel_size': 6, 'stride': 3, 'causal': True,
            'resample': 2, 'growth': 1.5, 'max_hidden': 48,
            'normalize': True, 'glu': False, 'rescale': 0.1
        }
    ]
    
    results = []
    
    for i, config in enumerate(model_configs):
        config_copy = config.copy()
        model_name = config_copy.pop('name')
        
        print(f"[{i+1}/{len(model_configs)}] 테스트 중: {model_name}")
        print(f"  설정: hidden={config_copy['hidden']}, depth={config_copy['depth']}, "
              f"resample={config_copy['resample']}, growth={config_copy['growth']}")
        
        result = test_model_rtf(config_copy, num_tests=3, audio_duration=4.0)
        result['name'] = model_name
        results.append(result)
        
        if result['success']:
            print(f"  ✅ 성공: RTF={result['avg_rtf']:.3f}, "
                  f"모델 크기={result['model_size_mb']:.1f}MB")
            if result['avg_rtf'] < 1.0:
                print(f"     🎯 RTF < 1.0 달성!")
        else:
            print(f"  ❌ 실패: {result['error']}")
        print()
    
    # 결과 정리 및 출력
    print("=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    
    # 성공한 모델들만 필터링
    successful_results = [r for r in results if r['success']]
    
    if not successful_results:
        print("❌ 성공한 모델이 없습니다!")
        return
    
    # RTF 순으로 정렬
    successful_results.sort(key=lambda x: x['avg_rtf'])
    
    print(f"{'순위':<4} {'모델명':<20} {'RTF':<8} {'크기(MB)':<10} {'상태'}")
    print("-" * 60)
    
    rtf_under_1_models = []
    
    for i, result in enumerate(successful_results):
        status = "🎯 목표달성" if result['avg_rtf'] < 1.0 else "⚠️  목표미달"
        if result['avg_rtf'] < 1.0:
            rtf_under_1_models.append(result)
        
        print(f"{i+1:<4} {result['name']:<20} {result['avg_rtf']:<8.3f} "
              f"{result['model_size_mb']:<10.1f} {status}")
    
    print()
    
    if rtf_under_1_models:
        print("🎯 RTF < 1.0 달성 모델들:")
        print("-" * 40)
        for model in rtf_under_1_models:
            print(f"  • {model['name']}: RTF={model['avg_rtf']:.3f}, "
                  f"크기={model['model_size_mb']:.1f}MB")
            print(f"    설정: {model['config']}")
        
        best_model = rtf_under_1_models[0]
        print(f"\n🏆 최적 모델: {best_model['name']}")
        print(f"   RTF: {best_model['avg_rtf']:.3f}")
        print(f"   모델 크기: {best_model['model_size_mb']:.1f}MB")
        print(f"   설정: {best_model['config']}")
    else:
        print("❌ RTF < 1.0을 달성한 모델이 없습니다.")
        print("가장 빠른 모델:")
        best = successful_results[0]
        print(f"  {best['name']}: RTF={best['avg_rtf']:.3f}")
    
    # 결과를 파일로 저장
    results_file = Path('/home/test1/denoiser/rtf_test_results.txt')
    with open(results_file, 'w') as f:
        f.write("라즈베리파이 5 RTF 테스트 결과\n")
        f.write("=" * 50 + "\n\n")
        
        for result in successful_results:
            f.write(f"모델: {result['name']}\n")
            f.write(f"RTF: {result['avg_rtf']:.3f}\n")
            f.write(f"모델 크기: {result['model_size_mb']:.1f}MB\n")
            f.write(f"설정: {result['config']}\n")
            f.write("-" * 30 + "\n")
    
    print(f"\n📄 상세 결과가 {results_file}에 저장되었습니다.")

if __name__ == "__main__":
    main()
