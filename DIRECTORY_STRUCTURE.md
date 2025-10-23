# 디렉토리 구조 설정 가이드

## 현재 구조 (Phase 6)

```
/home/test1/denoiser/
├── models/
│   └── best.th              # Light-32-Depth4 체크포인트
├── test_realtime.py         # Phase 6 메인 스크립트
└── (기타 훈련 관련 파일들)
```

---

## 권장 구조 (Task A, C 포함)

```
/home/test1/denoiser/
├── README.md                           # 프로젝트 문서
├── .gitignore                          # Git 제외 파일
├── COMMIT_GUIDE.md                     # 커밋 가이드
├── requirements.txt                    # Python 의존성
│
├── models/                             # AI 모델
│   ├── best.th                        # Light-32-Depth4 (커스텀)
│   └── README.md                      # 모델 설명
│
├── configs/                            # 설정 파일 (Task A)
│   ├── filter_config.yaml             # 필터 파라미터
│   └── audio_config.yaml              # 오디오 설정
│
├── src/                                # 소스 코드
│   ├── __init__.py
│   │
│   ├── core/                          # 핵심 모듈
│   │   ├── __init__.py
│   │   ├── model_loader.py           # AI 모델 로딩 (교체 가능)
│   │   ├── audio_stream.py           # 오디오 I/O
│   │   └── buffer_manager.py         # 버퍼 관리
│   │
│   ├── filters/                       # Task A: 필터 체인
│   │   ├── __init__.py
│   │   ├── base.py                   # 필터 베이스 클래스
│   │   ├── pre_filters.py            # HPF, Impulse Suppressor
│   │   ├── post_filters.py           # Noise Gate, Limiter
│   │   └── filter_chain.py           # 통합 체인
│   │
│   ├── communication/                 # Task C: WiFi 통신
│   │   ├── __init__.py
│   │   ├── wifi_manager.py           # WiFi Direct 관리
│   │   ├── audio_sender.py           # UDP 송신
│   │   ├── audio_receiver.py         # UDP 수신
│   │   └── full_duplex.py            # 양방향 통신
│   │
│   └── utils/                         # 유틸리티
│       ├── __init__.py
│       ├── audio_device.py           # 디바이스 관리
│       ├── benchmark.py              # 성능 측정
│       └── logger.py                 # 로깅
│
├── scripts/                            # 실행 스크립트
│   ├── test_realtime.py              # Phase 6 (현재)
│   ├── test_realtime_original.py     # 원본 denoiser 테스트
│   ├── test_filters.py               # Task A 필터 테스트
│   ├── test_wifi.py                  # Task C WiFi 테스트
│   ├── run_local.py                  # 로컬 디노이징
│   ├── run_sender.py                 # 송신기 모드
│   ├── run_receiver.py               # 수신기 모드
│   └── run_tactical.py               # 최종 통합 시스템
│
├── tests/                              # 단위 테스트
│   ├── __init__.py
│   ├── test_filters.py
│   ├── test_model_loader.py
│   └── test_communication.py
│
├── notebooks/                          # Jupyter 분석 (선택)
│   └── performance_analysis.ipynb
│
├── data/                               # 테스트 데이터
│   ├── test_audio/
│   │   ├── clean_speech.wav
│   │   └── noisy_speech.wav
│   └── recordings/
│       └── (테스트 녹음 파일)
│
├── docs/                               # 추가 문서
│   ├── ARCHITECTURE.md                # 시스템 아키텍처
│   ├── FILTER_GUIDE.md                # Task A 필터 가이드
│   └── WIFI_SETUP.md                  # Task C WiFi 설정
│
└── utils/                              # 독립 실행 도구
    ├── check_audio_device.py          # 오디오 디바이스 확인
    ├── setup_wifi.sh                  # WiFi Direct 자동 설정
    └── benchmark_models.py            # 모델 성능 비교
```

---

## 설정 방법

### 1. 디렉토리 생성
```bash
cd /home/test1/denoiser

# 메인 디렉토리 생성
mkdir -p src/{core,filters,communication,utils}
mkdir -p configs scripts tests data/{test_audio,recordings} docs

# __init__.py 파일 생성
touch src/__init__.py
touch src/core/__init__.py
touch src/filters/__init__.py
touch src/communication/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py
```

### 2. 기존 파일 이동
```bash
# 현재 test_realtime.py를 scripts/로 이동
mv test_realtime.py scripts/

# 또는 심볼릭 링크 (호환성 유지)
ln -s scripts/test_realtime.py test_realtime.py
```

### 3. requirements.txt 생성
```bash
# 의존성 파일 생성
cat > requirements.txt << 'EOF'
torch>=2.5.0
sounddevice>=0.5.0
scipy>=1.14.0
numpy>=2.1.0
PyYAML>=6.0  # 설정 파일용
soundfile>=0.12.0  # 원본 denoiser용 (선택)
EOF
```

---

## Task A: 필터 모듈 구조 (예정)

```python
# src/filters/filter_chain.py
class FilterChain:
    def __init__(self, config_path):
        self.filters = []
        self.load_config(config_path)
    
    def process(self, audio):
        for filter in self.filters:
            audio = filter.process(audio)
        return audio

# configs/filter_config.yaml
filters:
  - name: HPF
    type: HighPassFilter
    cutoff: 80
    order: 4
  
  - name: ImpulseSuppressor
    type: ImpulseNoiseSuppressor
    threshold: -6
    attack: 0.001
    release: 0.1
  
  - name: AIDenoiser
    type: ModelDenoiser
    model: Light-32-Depth4  # 또는 dns48
    checkpoint: models/best.th
```

---

## Task C: 통신 모듈 구조 (예정)

```python
# src/communication/full_duplex.py
class TacticalComm:
    def __init__(self, role='A'):
        self.sender = AudioSender(role)
        self.receiver = AudioReceiver(role)
        self.filter_chain = FilterChain('configs/filter_config.yaml')
        self.model = ModelLoader.load('Light-32-Depth4')
    
    def start(self):
        # 송신 스레드
        threading.Thread(target=self._send_loop).start()
        # 수신 스레드
        threading.Thread(target=self._recv_loop).start()
```

---

## 실행 스크립트 예시 (Task A, C 통합 후)

### 로컬 디노이징
```bash
python scripts/run_local.py --model Light-32-Depth4 --filters configs/filter_config.yaml
```

### WiFi 통신 (RP5-A)
```bash
python scripts/run_tactical.py --role A --mode sender
```

### WiFi 통신 (RP5-B)
```bash
python scripts/run_tactical.py --role B --mode receiver
```

---

## 이점

### 1. 모듈화
- 각 기능이 독립적으로 테스트 가능
- 코드 재사용성 향상

### 2. 유지보수성
- 명확한 파일 구조
- 기능별 분리

### 3. 확장성
- 새 필터 추가 용이
- 다른 모델로 교체 간편

### 4. 협업 친화적
- 표준 Python 프로젝트 구조
- README, 문서 완비

---

## 다음 대화에서 적용

**대화 2 (Task A)**: `src/filters/` 모듈 구현  
**대화 3 (Task C)**: `src/communication/` 모듈 구현

현재는 문서만 준비하고, 실제 코드 마이그레이션은 다음 대화에서 진행합니다.
