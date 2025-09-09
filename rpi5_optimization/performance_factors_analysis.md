# 라즈베리파이 5 음성 디노이징 성능 최적화 가이드

## 1. 성능 지표 정의

### 실시간 성능 (RTF)
- **목표**: RTF < 1.0 (라즈베리파이 5에서)
- **측정**: 처리시간 / 오디오길이
- **중요도**: ⭐⭐⭐⭐⭐ (필수조건)

### 소음 제거 품질
- **PESQ**: 음성 품질 점수 (1.0~4.5, 높을수록 좋음)
- **STOI**: 음성 명료도 (0~1, 높을수록 좋음)
- **중요도**: ⭐⭐⭐⭐⭐ (핵심 품질)

## 2. 아키텍처 파라미터별 영향도

### 고영향 파라미터 (성능/품질 모두 중요)

| 파라미터 | 속도 영향 | 품질 영향 | 추천 최적화 |
|----------|-----------|-----------|-------------|
| `hidden` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 48→32→24→16 단계적 감소 |
| `depth` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 5→4→3 감소 (3 이하는 품질 급감) |
| `glu` | ⭐⭐⭐ | ⭐⭐ | True→False (파라미터 50% 감소) |
| `resample` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 4→2 (품질 trade-off 있음) |

### 중간영향 파라미터

| 파라미터 | 속도 영향 | 품질 영향 | 추천 최적화 |
|----------|-----------|-----------|-------------|
| `growth` | ⭐⭐⭐ | ⭐⭐⭐ | 2.0→1.5 감소 |
| `kernel_size` | ⭐⭐ | ⭐⭐⭐ | 8→6 (receptive field 고려) |
| `stride` | ⭐⭐ | ⭐⭐ | 4 유지 (변경 시 호환성 문제) |
| `max_hidden` | ⭐⭐ | ⭐⭐ | hidden*4로 제한 |

### 저영향 파라미터

| 파라미터 | 속도 영향 | 품질 영향 | 추천 설정 |
|----------|-----------|-----------|----------|
| `normalize` | ⭐ | ⭐⭐ | True 유지 |
| `rescale` | ⭐ | ⭐ | 0.1 유지 |
| `causal` | ⭐ | ⭐⭐ | True (실시간 필수) |

## 3. 최적화 전략

### Phase 1: 아키텍처 경량화
1. `glu=False` 설정 (즉시 50% 파라미터 감소)
2. `hidden` 48→32→24 단계적 감소
3. `depth` 5→4→3 감소
4. `resample` 4→2 변경 (필요시)

### Phase 2: 추론 최적화
1. **PyTorch JIT 컴파일**
   ```python
   model = torch.jit.script(model)
   ```

2. **INT8 Quantization**
   ```python
   model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
   ```

3. **ONNX 변환**
   ```python
   torch.onnx.export(model, dummy_input, "model.onnx")
   ```

### Phase 3: 시스템 최적화
1. CPU 성능 모드 설정
2. 메모리 스왑 최소화
3. PyTorch 스레드 수 최적화
4. 온도 관리 (라즈베리파이 쿨링)

## 4. 성능 벤치마크 예상치

### 라즈베리파이 5 (16GB) 예상 RTF

| 모델 구성 | 예상 RTF | 예상 품질 | 메모리 사용량 |
|-----------|----------|-----------|---------------|
| hidden=16, depth=3, glu=False | 0.3-0.5 | 낮음 | ~200MB |
| hidden=24, depth=3, glu=False | 0.4-0.6 | 보통-낮음 | ~300MB |
| hidden=32, depth=3, glu=False | 0.5-0.7 | 보통 | ~400MB |
| hidden=32, depth=4, glu=False | 0.7-0.9 | 보통-좋음 | ~500MB |
| hidden=40, depth=4, glu=False | 0.8-1.0 | 좋음 | ~600MB |
| hidden=48, depth=4, glu=False | 0.9-1.2 | 좋음 | ~700MB |

## 5. 품질 vs 성능 권장 설정

### 최고 성능 우선 (RTF < 0.5)
```python
config = {
    'hidden': 24, 'depth': 3, 'glu': False,
    'resample': 2, 'growth': 1.5, 'kernel_size': 6
}
```

### 균형 설정 (RTF < 0.8, 적당한 품질)
```python
config = {
    'hidden': 32, 'depth': 3, 'glu': False,
    'resample': 2, 'growth': 1.5, 'kernel_size': 8
}
```

### 품질 우선 (RTF < 1.0, 높은 품질)
```python
config = {
    'hidden': 40, 'depth': 4, 'glu': False,
    'resample': 2, 'growth': 1.5, 'kernel_size': 8
}
```

## 6. 테스트 우선순위

1. **1단계**: 빠른 RTF 테스트로 실시간 가능 모델 식별
2. **2단계**: 실시간 가능 모델들의 품질 평가 (PESQ/STOI)
3. **3단계**: 최적 모델 선정 및 재훈련
4. **4단계**: 추론 최적화 적용 (Quantization, ONNX)
5. **5단계**: 실제 라즈베리파이 배포 테스트

이 가이드를 참고하여 단계적으로 최적화를 진행하시면 됩니다!
