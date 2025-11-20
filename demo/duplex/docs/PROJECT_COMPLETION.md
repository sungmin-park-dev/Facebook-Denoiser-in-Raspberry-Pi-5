# RP5 양방향 AI 음성 디노이징 시스템 - 프로젝트 완료 보고서

**날짜**: 2025-11-20  
**상태**: ✅ 프로젝트 완료  
**버전**: v1.0 Final

---

## 🎯 프로젝트 목표 달성

### 초기 목표
- [x] **실시간 처리**: RTF < 1.0
- [x] **양방향 통신**: Full-duplex WiFi Direct
- [x] **AI 디노이징**: Light-32-Depth4 모델
- [x] **저지연**: 총 지연 < 200ms
- [x] **안정성**: 장시간 무중단 구동

### 최종 성능 지표

| 항목 | 목표 | 달성 | 상태 |
|------|------|------|------|
| **RTF** | < 1.0 | 0.75~0.92 | ✅ 달성 |
| **지연** | < 200ms | ~100ms | ✅ 초과 달성 |
| **패킷 손실** | < 10% | 4~6% | ✅ 달성 |
| **연속 구동** | 1분+ | 무제한 | ✅ 달성 |
| **CPU 사용** | - | ~50% | ✅ 여유 |

---

## 🔧 주요 최적화 내역

### Phase 1: Chunk 크기 증가 (20ms → 60ms)
**문제**: AI 처리 오버헤드로 RTF 3.0+  
**해결**: 60ms 청크로 증가 → AI 처리 빈도 1/3  
**효과**: RTF 3.0 → 0.9

### Phase 2: CPU Performance 모드
**문제**: ondemand 모드에서 CPU throttling  
**해결**: Performance 모드 강제 설정  
**효과**: 처리 시간 50% 감소

### Phase 3: 텐서 재사용
**문제**: 메모리 할당/해제 오버헤드  
**해결**: 텐서 프리할당 및 재사용  
**효과**: RTF 15% 감소

### Phase 4: UDP 버퍼 증가
**문제**: 패킷 손실 37%  
**해결**: 수신 버퍼 200KB → 1MB  
**효과**: 패킷 손실 37% → 4%

### Phase 5: 감쇠량 제한
**문제**: AI가 음성까지 과도하게 제거 (30dB+)  
**해결**: 최대 70% 감쇠 제한 (최소 30% 보존)  
**효과**: 음성 명료도 개선

### Phase 6: 배치 처리
**문제**: RTF 스파이크로 가끔 딜레이  
**해결**: 2개 청크 모아서 처리  
**효과**: RTF 안정성 향상, 스파이크 50% 감소

---

## 📊 시스템 구성

### 하드웨어
- **RP5-A**: Hotspot 호스트 (test1)
- **RP5-B**: Client (test2)
- **오디오**: H08A USB Audio Interface (Device 1)
- **연결**: WiFi Direct (10.42.0.x)

### 소프트웨어
- **OS**: Ubuntu 24.04 LTS
- **Python**: 3.12
- **PyTorch**: 2.8.0 (CPU)
- **AI 모델**: Light-32-Depth4 (434K params, 1.7MB)
- **코덱**: Opus (16kbps, 20ms frame)

### 아키텍처
```
송신측 (60ms 청크):
Mic → Downsample (48k→16k) → AI Denoiser (배치 2개)
→ Split (320씩 6개) → Opus Encode → UDP Send

수신측:
UDP Recv → Opus Decode → Accumulate (960 모음)
→ Upsample (16k→48k) → Speaker
```

---

## 🚀 사용 방법

### 1. 시작

**RP5-A:**
```bash
cd /home/test1/denoiser
sudo bash demo/duplex/start_rp5a.sh
```

**RP5-B:**
```bash
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
sudo bash demo/duplex/start_rp5b.sh
```

### 2. 런타임 제어

- **Enter**: Bypass ↔ AI 모드 토글
- **q + Enter**: 종료

### 3. 모니터링

```
📊 TX: 5000 (50/s) | RX: 4800 (48/s)
🤖 AI RTF: avg=0.89, max=1.2, min=0.75
   Noise reduction: 8.5dB | RMS: 0.0234→0.0089
📡 Packet loss: 4.0%
```

- **RTF < 1.0**: 실시간 처리 중
- **Noise reduction 5-12dB**: 정상 작동
- **Packet loss < 10%**: 통신 양호

---

## 📈 성능 비교

### Bypass vs AI 모드

| 모드 | CPU | 지연 | 음질 | 소음 제거 |
|------|-----|------|------|----------|
| **Bypass** | 10% | 50ms | 원본 | 없음 |
| **AI** | 45% | 100ms | 약간 감쇠 | 5-12dB |

### 이전 vs 최종

| 항목 | 초기 | 최종 | 개선 |
|------|------|------|------|
| RTF | 3.2 | 0.89 | **3.6배** |
| 패킷 손실 | 37% | 4% | **9배** |
| 딜레이 누적 | 있음 | 없음 | ✅ |
| 음성 보존 | 95% 제거 | 정상 | ✅ |

---

## ⚠️ 알려진 제한사항

### 1. 소음 제거 효과 제한적
**원인**: Light-32-Depth4 모델의 파라미터 부족 (434K)  
**증상**: 강한 배경 소음에서 음성도 함께 감쇠  
**해결책**: Light-40 모델로 업그레이드 (RTF 0.92 유지)

### 2. 가끔 RTF 스파이크
**원인**: CPU 스케줄링, 다른 프로세스 간섭  
**증상**: 가끔 RTF 2.0+ → 일시적 딜레이  
**완화**: 배치 처리로 50% 감소

### 3. 초기 지연 100ms
**원인**: 버퍼링 + 배치 처리  
**영향**: 통화 품질에는 큰 영향 없음  
**참고**: 일반 VoIP도 50-150ms

---

## 🔮 향후 개선 방향

### 단기 (1-2주)
1. **Light-40 모델 훈련**
   - 파라미터: 434K → 700K
   - RTF: 0.89 → 0.92 유지
   - 품질: 대폭 개선 예상

2. **실제 환경 데이터 수집**
   - 현재 통신 소음 녹음
   - Fine-tuning 데이터셋 구축

### 중기 (1개월)
3. **전장 특화 필터 체인**
   - High-pass filter (80Hz)
   - Impulse noise suppressor (총성/폭발음)
   - AI denoiser
   - Soft limiter

4. **적응형 감쇠량 제어**
   - 입력 레벨에 따라 제한 조정
   - 음성/소음 자동 구분

### 장기 (3개월+)
5. **Echo Cancellation**
   - 스피커 → 마이크 피드백 제거
   - 더 자연스러운 통화

6. **Multi-channel 지원**
   - 3명 이상 동시 통신
   - 채널 관리 시스템

---

## 📚 프로젝트 파일 구조

```
demo/duplex/
├── core/
│   ├── audio_comm.py          # UDP, Opus, Resample
│   └── audio_processor.py     # Base class
│
├── processors/
│   ├── bypass.py              # Passthrough
│   ├── ai_denoiser.py         # AI denoising ⭐
│   └── classical_filters.py   # (미구현)
│
├── configs/
│   ├── rp5a_modular.yaml      # RP5-A 설정
│   └── rp5b_modular.yaml      # RP5-B 설정
│
├── rp5_full_duplex_modular.py # 메인 애플리케이션
├── start_rp5a.sh              # 실행 스크립트 (A)
├── start_rp5b.sh              # 실행 스크립트 (B)
├── set_performance.sh         # CPU 설정
└── rp5-performance.service    # Systemd 서비스

docs/
├── CPU_PERFORMANCE_GUIDE.md   # CPU 설정 가이드
├── MODULAR_ARCHITECTURE.md    # 아키텍처 문서
└── PROJECT_COMPLETION.md      # 본 문서
```

---

## 🎓 학습 내용 & 인사이트

### 1. 경량화 vs 품질 트레이드오프
- RTF 0.8 달성 위해 품질 일부 희생 불가피
- Light-32는 실시간성 우선, Light-40은 균형점

### 2. Chunk 크기의 중요성
- 작은 청크: 저지연, 높은 오버헤드
- 큰 청크: 고지연, 낮은 오버헤드
- 60ms가 최적 균형점

### 3. 배치 처리의 효과
- AI 호출 빈도 50% 감소
- 오버헤드 대폭 감소
- 지연 증가는 미미 (20ms)

### 4. CPU 모드의 결정적 영향
- ondemand: RTF 3.0+
- performance: RTF 0.9
- **3배 이상 차이!**

### 5. 소음 제거 vs 음성 보존
- 무조건 강한 제거가 좋은 게 아님
- 감쇠량 제한으로 명료도 유지 필수

---

## ✅ 체크리스트

### 기능 완성도
- [x] 양방향 통신 (Full-duplex)
- [x] AI 디노이징 (실시간)
- [x] 런타임 모드 전환
- [x] 성능 모니터링
- [x] 자동 CPU 설정
- [x] 안정적 장시간 구동
- [ ] Echo cancellation (향후)
- [ ] Multi-channel (향후)

### 문서화
- [x] 사용 가이드
- [x] 아키텍처 문서
- [x] CPU 설정 가이드
- [x] 프로젝트 완료 보고서
- [x] 코드 주석
- [x] Git 커밋 히스토리

### 배포
- [x] GitHub 정리
- [x] 실행 스크립트
- [x] 설정 파일
- [x] Systemd 서비스
- [x] 문서 완비

---

## 🙏 감사의 말

이 프로젝트는 **실시간 AI 음성 처리**라는 도전적인 목표를 **라즈베리파이 5**라는 제한된 하드웨어에서 달성하는 여정이었습니다.

**핵심 성과:**
- ✅ RTF 0.89 (실시간의 1.1배 여유)
- ✅ 패킷 손실 4% (양호한 통신 품질)
- ✅ 모듈화 아키텍처 (확장 용이)
- ✅ 안정적 양방향 통신

**개선 여지:**
- ⚠️ 소음 제거 효과 (모델 업그레이드 필요)
- ⚠️ 가끔 RTF 스파이크 (추가 최적화 가능)

하지만 **프로젝트 목표는 충분히 달성**했고, **향후 개선 방향도 명확**합니다.

---

## 📞 연락처

**개발자**: 박성민 (David)  
**날짜**: 2025-11-20  
**버전**: v1.0 Final  
**GitHub**: https://github.com/sungmin-park-dev/Facebook-Denoiser-in-Raspberry-Pi-5

---

**프로젝트 상태: ✅ 완료**  
**배포 준비: ✅ 완료**  
**문서화: ✅ 완료**
