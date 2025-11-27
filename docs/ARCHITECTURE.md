# RP5 실시간 디노이징 시스템 아키텍처

## 📋 개요

본 문서는 Raspberry Pi 5 실시간 음성 디노이징 시스템의 전체 아키텍처, 디렉토리 구조, 모듈 설계를 설명합니다.

---

## 🏗️ 시스템 아키텍처

### 전체 구성도

```
┌─────────────────────────────────────────────────────────┐
│                   RP5 Denoising System                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │  Audio I/O   │ ←→ │  Processing  │ ←→ │  Network │ │
│  │   (48kHz)    │    │    (16kHz)   │    │   (UDP)  │ │
│  └──────────────┘    └──────────────┘    └──────────┘ │
│         ↕                    ↕                  ↕       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │ sounddevice  │    │ AI Denoiser  │    │   Opus   │ │
│  │   + ALSA     │    │ Light-32-D4  │    │  Codec   │ │
│  └──────────────┘    └──────────────┘    └──────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Phase별 발전

**Phase 1-5**: 로컬 처리
- Mic → AI Denoiser → Speaker
- RTF 최적화 (0.071)
- 48kHz ↔ 16kHz 리샘플링

**Phase 6**: 실시간 스트리밍
- 버퍼 기반 멀티스레드
- TorchScript 컴파일
- 2초 출력 버퍼

**Phase 6.5**: 원본 모델 비교
- dns48, dns64 RTF 측정
- Light-32-Depth4 검증

**Phase 7 (Full-Duplex)**: 양방향 통신
- WiFi Direct 연결
- 모듈화 아키텍처

---

## 📁 디렉토리 구조

### 프로젝트 루트

```
Facebook-Denoiser-in-Raspberry-Pi-5/
├── README.md                           # 프로젝트 메인 문서
├── CLAUDE.md                           # Claude AI 작업 지침
├── requirements.txt                    # Python 의존성
├── setup.py                            # 패키지 설치
├── train.py                            # 모델 훈련 (Hydra)
│
├── models/                             # AI 모델 체크포인트
│   ├── valentini_light32_60ep/        # Valentini 훈련 모델
│   └── debug_standard48_1ep/          # 디버그용
│
├── denoiser/                           # Facebook 원본 코드 (변경 금지)
│   ├── demucs.py                      # Demucs 모델 정의
│   ├── pretrained.py                  # 사전훈련 모델 로더
│   └── audio.py                       # 오디오 처리 유틸
│
├── conf/                               # Hydra 설정
│   ├── config.yaml                    # 메인 설정
│   └── dset/                          # 데이터셋 설정
│       ├── debug.yaml
│       └── valentini.yaml
│
├── dataset/                            # 훈련 데이터
│   ├── debug/                         # 디버그용 (1분)
│   └── valentini_archive/             # Valentini (4-8시간)
│
├── demo/                               # 실시간 데모
│   ├── duplex/                        # WiFi Direct 양방향 통신
│   ├── duplex_macbook_hotspot/        # MacBook Hotspot 버전
│   ├── simplex/                       # 단방향 통신
│   └── Mac_and_bluetooth_speaker_realtime/
│
├── archive/                            # 아카이브
│   └── experiments/duplex_debug/      # Duplex 디버그 기록
│
├── src/                                # 공통 모듈
│   └── communication/codec.py         # Opus 코덱
│
├── audio_pipeline/                     # 오디오 처리
│   └── core/model_loader.py           # 모델 로더
│
└── docs/                               # 프로젝트 문서
    ├── ARCHITECTURE.md                # 본 문서
    ├── SETUP_GUIDE.md                 # 설치 및 설정
    └── COMPLETED_PHASES.md            # Phase 완료 기록
```

---

## 🔧 Full-Duplex 모듈화 아키텍처

### demo/duplex/ 구조

```
demo/duplex/
├── core/                              # 핵심 모듈
│   ├── audio_comm.py                 # UDP + Opus + Resample
│   └── audio_processor.py            # 처리 인터페이스 (ABC)
│
├── processors/                        # 오디오 프로세서
│   ├── bypass.py                     # 처리 없음
│   ├── ai_denoiser.py                # AI 디노이징
│   └── classical_filters.py          # 고전적 필터 (예정)
│
├── configs/                           # 설정 파일
│   ├── rp5a_config.yaml              # WiFi Direct (AP)
│   ├── rp5b_config.yaml              # WiFi Direct (Client)
│   ├── rp5a_modular.yaml             # 모듈화 버전
│   └── rp5b_modular.yaml
│
├── rp5_full_duplex_modular.py        # 메인 스크립트
├── start_modular_a.py                # RP5-A 실행
├── start_modular_b.py                # RP5-B 실행
├── start_rp5a.sh                     # CPU + 통신 통합
├── start_rp5b.sh
└── set_performance.sh                # CPU governor 설정
```

### 모듈 역할

#### 1. core/audio_comm.py
- UDP 송수신
- Opus 인코딩/디코딩
- 48kHz ↔ 16kHz 리샘플링
- Queue 관리

#### 2. core/audio_processor.py
- Abstract Base Class
- 모든 프로세서의 공통 인터페이스

```python
class AudioProcessor(ABC):
    @abstractmethod
    def process(self, audio: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass
```

#### 3. processors/
- `bypass.py`: Direct passthrough
- `ai_denoiser.py`: Light-32-Depth4 AI 디노이징
- `classical_filters.py`: 전통적 필터 (예정)

### 토글 시스템

실행 중 Enter 키로 프로세서 전환:
```
Bypass → AI Denoiser → Classical Filters → Bypass (순환)
```

---

## 🌐 네트워크 구성

### WiFi Direct (demo/duplex/)

```
RP5-A (10.42.0.1)  ←─ WiFi Direct ─→  RP5-B (10.42.0.224)
   AP 모드                               Client 모드
 UDP 9999 send                         UDP 9998 send
 UDP 9998 recv                         UDP 9999 recv
```

### MacBook Hotspot (demo/duplex_macbook_hotspot/)

```
MacBook (192.168.2.1)
    ↓ Personal Hotspot
    ├─ RP5-A (192.168.2.2) ←→ UDP 9998/9999 ←→ RP5-B (192.168.2.3)
```

---

## 📊 성능 설정

### RP5 CPU Governor

양방향 통신 시 AI 처리 딜레이 누적 방지:

```bash
# Performance 모드 (2.4GHz 고정)
sudo bash start_rp5a.sh  # CPU 설정 + 통신 시작 통합
```

| 모드 | CPU 주파수 | AI 처리 시간 | RTF | 딜레이 누적 |
|------|-----------|-------------|-----|----------|
| Ondemand | 600MHz~2.4GHz | 20~30ms | >1.0 | ❌ 있음 |
| Performance | 2.4GHz 고정 | 1~2ms | 0.05~0.1 | ✅ 없음 |

---

## 🔗 관련 문서

- 설치 및 CPU 설정: `SETUP_GUIDE.md`
- 완료 Phase 기록: `COMPLETED_PHASES.md`
- 프로젝트 개요: `/README.md`
- MacBook Hotspot 설정: `demo/duplex_macbook_hotspot/README.md`

---

**작성일**: 2025-11-26
**버전**: v1.0
**통합 문서**: MODULAR_ARCHITECTURE.md + DIRECTORY_STRUCTURE.md
