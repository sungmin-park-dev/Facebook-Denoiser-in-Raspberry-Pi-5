# Real-Time Audio Denoising System for Raspberry Pi 5

**최종 업데이트**: 2025-01-23 
**작성자**: David(박성민) & Claude 
**상태**: Phase 6.5 완료, Task A 준비 중

---

## 📋 프로젝트 개요

라즈베리파이 5에서 실시간으로 작동하는 음성 디노이징 시스템 개발 프로젝트입니다. 전장 환경에서의 통신 품질 개선을 목표로 하며, 최종적으로 WiFi Direct를 통한 양방향 실시간 음성 통신 시스템을 구축합니다.

### 핵심 목표

- ✅ **실시간 처리**: RTF < 1.0 (실시간보다 빠름)
- ✅ **저지연**: 전체 latency < 200ms
- ✅ **고품질**: 배경 소음 효과적 제거
- 🔄 **양방향 통신**: 동시 송수신 가능
- 🔄 **전장 환경 특화**: 폭발음, 총성 등 극단 소음 처리

### 기술 스택

- **원본** (2020): PyTorch 1.5, torchaudio 0.5, Hydra 0.11
- **현재** (Migration 완료): PyTorch 2.8.0, torchaudio 2.8.0, Hydra 1.1+, Python 3.12

---

## 🏗️ 3-Tier 개발 환경

|환경|맥북 🍎|Colab ☁️|RP5 🔧|
|---|---|---|---|
|설정 관리|✅|❌|❌|
|Debug 테스트|✅|✅|❌|
|Valentini 훈련|❌|✅|❌|
|RTF 테스트|❌|❌|✅|
|실시간 구동|❌|❌|✅|

### 맥북 (설정 관리 허브)

- **역할**: 코드 수정, GitHub 동기화, Debug 테스트
- **환경**: Apple M1, macOS 15.6.1, Python 3.12
- **경로**: `/Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5`
- **상태**: ✅ Migration 완료, Debug 훈련 성공 (STOI=0.8054)

```bash
# 환경 활성화
conda activate denoiser_modern
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5
```

### Colab (훈련 전용)

- **역할**: Valentini 데이터셋 본격 훈련 (GPU 필수, 4-8시간)
- **환경**: GPU T4, Python 3.10+, Google Drive 연동
- **데이터**: `/content/drive/MyDrive/Colab Notebooks/ARMY Projects/valentini_dataset/`
- **상태**: ✅ Debug 테스트 완료 (STOI=0.8056), Valentini 훈련 준비 중

### 라즈베리파이 5 (배포 및 실행)

- **역할**: 최종 모델 검증 및 실시간 구동
- **환경**: Cortex-A76 4코어, Ubuntu 24.04 LTS, 8GB RAM, CPU only
- **경로**: `/home/test1/denoiser`
- **상태**: ✅ Phase 6.5 완료 (실시간 구동 안정화)

---

## 🚀 프로젝트 진행 상황

### ✅ Phase 1: RTF 최적화 (RP5)

**목표**: 실시간 처리 가능한 경량 모델 탐색

|모델|RTF|크기|상태|
|---|---|---|---|
|**Light-32-Depth4**|**0.834**|1.7MB|✅ 최적|
|Light-40|0.905|2.6MB|✅ 대안|
|Standard-Light-48|1.167|3.7MB|❌ 실시간 불가|

**핵심 파라미터** (변경 금지):

```yaml
hidden: 32
depth: 4
resample: 2        # 가장 큰 영향 (2.5배 성능 향상)
glu: false
growth: 1.5
kernel_size: 8     # Demucs 핵심 설계, 변경 금지
stride: 4          # Demucs 핵심 설계, 변경 금지
```

**성능 영향 순위** (RP5 벤치마킹):

1. resample=2 ⭐⭐⭐⭐⭐ (2.5배 향상)
2. hidden=32 ⭐⭐⭐⭐⭐ (28% 개선)
3. depth=4 ⭐⭐⭐⭐ (28% 개선)
4. glu=false ⭐⭐⭐ (파라미터 50% 감소)
5. growth=1.5 ⭐⭐⭐ (경량화)

---

### ✅ Phase 2: Migration 완료 (Mac에서 진행)

**목표**: PyTorch 2.8 + Hydra 1.1+ 호환

#### 주요 수정 사항

**1. Hydra 1.1+ 호환 (train.py)**

```python
# 수정 전
@hydra.main(config_path="conf/config.yaml")

# 수정 후
@hydra.main(config_path="conf", config_name="config", version_base="1.1")
```

**2. Config 구조 변경 (conf/config.yaml)**

```yaml
defaults:
  - dset: debug
  - override hydra/job_logging: colorlog
  - override hydra/hydra_logging: colorlog
  - _self_  # 핵심: 현재 config가 덮어씌워지지 않도록
```

**3. Dataset YAML 구조 변경 (conf/dset/*.yaml)**

```yaml
# 수정 전
dset:
  train: egs/debug/tr
  matching: sort

# 수정 후 (dset: 키 완전 제거)
train: egs/debug/tr
matching: sort
```

**4. torchaudio API 변경 (denoiser/audio.py)**

```python
# 수정 전
torchaudio.load(..., offset=start)

# 수정 후
torchaudio.load(..., frame_offset=start)
```

**결과**: Debug 훈련 성공 (1분, STOI=0.8054, best.th 72MB 생성)

---

### ✅ Phase 3: Colab Debug 테스트

**목표**: Colab 환경에서 훈련 가능 여부 검증

**주요 작업**:
- setup.py 수정: `hydra_core>=1.3.2`, `torch>=2.0` 반영
- requirements.txt 업데이트: Mac/Colab 버전 통일
- Debug 훈련 성공: 2 epochs, 3분 소요
- **STOI**: 0.8056 (목표 0.75 초과 달성) ✅
- **PESQ**: 1.25 (Debug용, 본 훈련 아님)


**핵심 해결**:

- `pip install -e .` 시 Hydra 다운그레이드 문제 해결
- Mac-Colab 환경 완전히 통일 (Hydra 1.3.2, PyTorch 2.8.0)

---

### ✅ Phase 4: Valentini 본격 훈련

**목표**: Light-32-Depth4 모델로 Valentini 데이터셋 훈련

**사전 준비**:

- ✅ Valentini 데이터셋 Google Drive 업로드
- ✅ `conf/dset/valentini.yaml` 경로 설정
- 🔄 loss 변화 그래프 특정 epoch마다 업데이트
- 🔄 pesq/stoi 평가 특정 epoch마다 업데이트
- 🔄 Colab 훈련 시작 (100 epochs, 4-8시간)

**훈련 설정**:

```yaml
epochs: 100
batch_size: 16
device: cuda
# Light-32-Depth4 파라미터 적용
hidden: 32
depth: 4
resample: 2
glu: false
```

**예상 결과**:

- 훈련 시간: 4-8시간 (GPU T4 기준)
- 목표: PESQ > 2.5, STOI > 0.85
- 모델 크기: ~2-3MB

---

### ✅ Phase 5: 오디오 하드웨어 통합

**목표**: RP5에 USB 오디오 인터페이스 연결 및 설정

**하드웨어 환경**:

```
Device: H08A Audio USB (hw:1,0)
- Input Channels: 2 (Stereo)
- Output Channels: 2 (Stereo)
- Sample Rate: 48kHz
```

**구현 사항**:

- H08A USB 오디오 설정
- 48kHz ↔ 16kHz 리샘플링 구현
- sounddevice 라이브러리 통합
- ALSA 채널 설정 해결 (`channels=2`)

**리샘플링 구현**:

```python
# Downsample: 48kHz → 16kHz
audio_16k = signal.resample_poly(audio_48k, 1, 3)

# Upsample: 16kHz → 48kHz
audio_48k = signal.resample_poly(audio_16k, 3, 1)
```

---

### ✅ Phase 6: 실시간 스트리밍 구현

**목표**: 버퍼 기반 실시간 오디오 처리 시스템

**아키텍처**:

```
Mic Input (48kHz)
    ↓
[Input Thread] → Resample (16kHz) → Processing Queue
    ↓
[Processing Thread] → AI Denoiser → Output Queue
    ↓
[Output Thread] → Resample (48kHz) → Speaker (2초 버퍼)
```

**핵심 기술**:

1. **버퍼 기반 스트리밍**
    
    ```python
    BUFFER_SIZE = 96000  # 48kHz * 2초
    output_buffer = deque(maxlen=BUFFER_SIZE)
    ```
    
2. **멀티스레드 처리**
    
    - Input Callback: 마이크 → 처리 큐
    - Processing Thread: AI 디노이징
    - Output Callback: 버퍼 → 스피커
3. **TorchScript 컴파일**
    
    ```python
    dummy_input = torch.randn(1, 1, CHUNK // 3)
    model = torch.jit.trace(model, dummy_input)
    # 추론 속도 20-30% 향상
    ```
    

**최종 성능 (Light-32-Depth4)**:

```
============================================================
📊 Final Stats:
   Model: Light-32-Depth4
   Parameters: 434,177 (1.67MB)
   
   Average RTF: 0.071 (실시간 대비 14배 여유)
   Max RTF: 0.095
   Min RTF: 0.065
   
   Latency: ~2초 (버퍼 기반, 끊김 없음)
   Audio Quality: 배경 소음 일부 제거, 음성 명료도 유지
   Stability: 장시간 무중단 구동 확인
============================================================
```

---

### ✅ Phase 6.5: 원본 Denoiser 모델 테스트

**목표**: Facebook Research 사전 훈련 모델 성능 비교

**테스트 모델**:
- dns48 (18.87M params)
- dns64 (33.53M params)
- master64 (참고용)

**성능 비교표**:

| Model                     | Parameters | Size   | RTF       | Real-time     |
| ------------------------- | ---------- | ------ | --------- | ------------- |
| **Light-32-Depth4** (커스텀) | 0.43M      | 1.67MB | **0.071** | ✅ 14배 여유      |
| **dns48** (원본)            | 18.87M     | ~72MB  | 1.484     | ❌ Overflow 발생 |
| **dns64** (원본)            | 33.53M     | ~128MB | 1.887     | ❌ Overflow 발생 |

**결론**:
- 원본 denoiser 모델은 RP5에서 실시간 처리 불가능
- Light-32-Depth4가 RP5 최적 모델
- 품질 vs 속도 트레이드오프: 실시간성 우선

**실행 방법**:

```bash
# Light-32-Depth4 (커스텀)
/home/test1/venv/bin/python test_realtime.py

# 원본 모델 테스트 (dns48, dns64)
/home/test1/venv/bin/python test_realtime_original.py
```

---

## 🚧 진행 예정 작업

### 🎯 Task A: 전장 특화 필터 체인 구현

#### 현재 문제점 (Phase 6.5 실제 테스트 결과)
1. ❌ **사용자 음성 왜곡**: Light-32-Depth4 과도한 경량화로 인한 디테일 손실
2. ❌ **총성/폭발음 효과 낮음**: 학습 데이터에 극단 소음 부재
3. ❌ **헬기 소리 부자연스러움**: 시간에 따라 변하는 소음 처리 미흡

#### 구현 계획: 4단계 필터 시스템
```
Input Audio (48kHz)
    ↓
[1] HPF (80Hz)
    └─ 차량/헬기 저주파 럼블 제거
    ↓
[2] Impulse Noise Suppressor ⭐ 핵심
    └─ 총성/폭발음 피크 선제 제한
    └─ Fast Attack Compression (Threshold=-6dB, Ratio=10:1, Attack=0.1ms)
    ↓
[3] AI Denoiser (Light-32-Depth4)
    └─ 배경 소음 제거 (향후 Light-40으로 업그레이드 예정)
    ↓
[4] Soft Limiter
    └─ 최종 피크 제한 (클리핑 방지)
    ↓
Output (16kHz for transmission)
```

#### 예상 성능
- **Total RTF**: ~0.09 (여전히 실시간의 11배 여유)
- **Latency 증가**: +15ms (총 ~115ms)
- **품질 개선**: 
  - 총성/폭발음 -15dB 감쇠 (문제 2 부분 해결)
  - 저주파 럼블 제거 (문제 3 부분 해결)
  - 클리핑 완전 방지

#### 기술 요구사항
- ✅ **모듈화 설계**: 각 필터 독립 모듈
- ✅ **설정 파일**: 파라미터 외부 설정 (config.yaml)
- ✅ **실시간 모니터링**: RTF, 버퍼 상태, 필터별 성능

#### 향후 개선 계획 (Phase A.2)
1. **모델 업그레이드**: Light-32 → Light-40 (음성 왜곡 근본 해결)
   - RTF: 0.09 → 0.925 (여전히 실시간 가능)
   - 파라미터: 434K → ~700K (1.6배 증가)
   - Valentini 재훈련 필요 (4-8시간)

2. **전장 소음 데이터 증강**: 헬기/총성/폭발음 학습
   - helicopter_noise (30%)
   - gunshot_noise (20%)
   - explosion_noise (10%)
   - 훈련 시간: 4-8시간 (Colab GPU)
---

### 🎯 Task B: WiFi Direct 양방향 통신

#### 목표

라우터 없이 RP5 간 직접 연결하여 전화와 같은 실시간 양방향 음성 통신 구현

#### 시스템 아키텍처

```
RP5-A (지휘소)                    RP5-B (전방)
├─ Mic Thread                     ├─ Mic Thread
│  └─ Filter+AI → Encode → UDP    │  └─ Filter+AI → Encode → UDP
├─ Speaker Thread                 ├─ Speaker Thread
│  └─ UDP ← Decode ← Filter       │  └─ UDP ← Decode ← Filter
└─ WiFi AP (192.168.4.1)          └─ WiFi Client (192.168.4.2)
```

#### 구현 단계

**Step 1: WiFi Direct 설정**

```bash
# RP5-A: Access Point
sudo nmcli device wifi hotspot ssid "TacticalComm" password "secure123"

# RP5-B: Client
sudo nmcli device wifi connect "TacticalComm" password "secure123"
```

**Step 2: UDP 오디오 스트리밍**

- Codec: Opus (16kbps, 저지연 최적화)
- Protocol: UDP (RTP)
- Ports: 5000 (A→B), 5001 (B→A)

**Step 3: Full-Duplex 통합**

- 독립적인 송신/수신 스레드
- 동시 디노이징 처리
- Echo cancellation (선택)

#### 예상 성능

- **총 지연시간**: 100-150ms
    - 필터링: 20ms
    - 인코딩: 10ms
    - 전송: 20-50ms
    - 디코딩: 10ms
    - 출력 버퍼: 50ms
- **대역폭**: ~20kbps (양방향 40kbps)
- **통신 범위**: WiFi Direct (~30m 실내, ~100m 야외)

#### 디렉토리 구조

```
denoiser/
├── communication/                 # [예정] Task C 통신 모듈
│   ├── __init__.py
│   ├── wifi_setup.sh
│   ├── audio_sender.py
│   ├── audio_receiver.py
│   └── full_duplex.py            # 최종 통합 시스템
```

---

## 📁 디렉토리 구조

```
denoiser/
├── models/
│   ├── best.th                    # Light-32-Depth4 체크포인트
│   └── (훈련 관련 파일들)
├── test_realtime.py               # Phase 6 최종 버전 (Light-32-Depth4)
├── test_realtime_original.py      # 원본 denoiser 테스트용
├── filters/                       # [예정] Task A 필터 모듈
│   ├── __init__.py
│   ├── highpass_filter.py        # [1] HPF (80Hz)
│   ├── impulse_suppressor.py     # [2] Fast Attack Compressor
│   ├── soft_limiter.py           # [4] 최종 피크 제한
│   └── config.yaml               # 필터 파라미터 설정
├── communication/                 # [예정] Task C 통신 모듈
│   ├── __init__.py
│   ├── wifi_setup.sh
│   ├── audio_sender.py
│   ├── audio_receiver.py
│   └── full_duplex.py            # 최종 통합 시스템
├── utils/
│   ├── check_audio_device.py     # 오디오 디바이스 확인 도구
│   └── benchmark.py              # 성능 측정 도구
├── conf/
│   ├── config.yaml               # Hydra 메인 설정
│   └── dset/
│       ├── debug.yaml            # Debug 데이터셋
│       └── valentini.yaml        # Valentini 데이터셋
├── setup.py                       # 패키지 설치 설정
├── requirements.txt               # 의존성 패키지
└── README.md                      # 본 문서
```

---

## ⚙️ 설치 및 실행

### 환경 설정 (RP5)

```bash
# 가상환경 생성
python3 -m venv ~/venv
source ~/venv/bin/activate

# 의존성 설치
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install sounddevice numpy scipy

# 원본 denoiser 모델 사용 시
pip install soundfile
```

### 실행 방법

#### Phase 6: Light-32-Depth4 모델

```bash
cd /home/test1/denoiser
/home/test1/venv/bin/python test_realtime.py
```

#### 원본 denoiser 모델 테스트

```bash
# dns48, dns64, master64 중 선택 (코드 내 MODEL_NAME 변경)
/home/test1/venv/bin/python test_realtime_original.py
```

#### 오디오 디바이스 확인

```bash
/home/test1/venv/bin/python utils/check_audio_device.py
```

---

## 📊 성능 벤치마크

### Light-32-Depth4 (Phase 6)

```
============================================================
📊 Final Stats:
   Chunks processed: 100+
   Runtime: 60+ seconds
   Avg RTF: 0.071
   Max RTF: 0.095
   Min RTF: 0.065
   Buffer: Stable (~2000ms)
   Status: ✅ 실시간 구동 안정
============================================================
```

### 모델 비교 (RP5 환경)

|Metric|Light-32-Depth4|dns48|dns64|
|---|---|---|---|
|Params|434K|18.87M|33.53M|
|Size|1.67MB|~72MB|~128MB|
|RTF|0.071|1.484|1.887|
|Real-time|✅|❌|❌|
|Quality|⭐⭐⭐|⭐⭐⭐⭐⭐|⭐⭐⭐⭐⭐⭐|

---

## 🛠️ 기술 스택

### 프레임워크 & 라이브러리

- **PyTorch**: 2.5.1+cpu (모델 추론)
- **sounddevice**: 0.5.1 (오디오 I/O)
- **scipy**: 1.14.1 (리샘플링)
- **numpy**: 2.1.3 (배열 처리)

### 시스템 레벨

- **ALSA**: 오디오 하드웨어 드라이버
- **PortAudio**: sounddevice 백엔드
- **NetworkManager**: WiFi Direct 관리 (Task C)

---

## 🔧 주요 기술 구현

### 1. 리샘플링 (48kHz ↔ 16kHz)

```python
# Downsample
audio_16k = signal.resample_poly(audio_48k, 1, 3)

# Upsample
audio_48k = signal.resample_poly(audio_16k, 3, 1)
```

### 2. 버퍼 기반 스트리밍

```python
# 2초 출력 버퍼 (끊김 방지)
BUFFER_SIZE = 96000  # 48kHz * 2초
output_buffer = deque(maxlen=BUFFER_SIZE)
```

### 3. 멀티스레드 처리

```python
# 독립 스레드
- Input Callback: 마이크 → 처리 큐
- Processing Thread: AI 디노이징
- Output Callback: 버퍼 → 스피커
```

### 4. TorchScript 컴파일

```python
# 추론 속도 20-30% 향상
dummy_input = torch.randn(1, 1, CHUNK // 3)
model = torch.jit.trace(model, dummy_input)
```

---

## 🐛 문제 해결 (Troubleshooting)

### 1. ALSA 채널 오류

```
Error: Invalid number of channels [PaErrorCode -9998]

해결: H08A는 스테레오(2채널) → channels=2 설정
```

### 2. Input Overflow 경고

```
⚠️ Input: input overflow

원인: 처리 속도가 입력 속도보다 느림 (RTF > 1.0)
해결: 더 가벼운 모델 사용 (Light-32-Depth4)
```

### 3. 모델 로딩 실패

```bash
# torch.hub 캐시 초기화
rm -rf ~/.cache/torch/hub
```

### 4. Hydra 버전 충돌

```bash
# setup.py 의존성 확인
pip install hydra-core>=1.3.2

# 또는 requirements.txt 사용
pip install -r requirements.txt
```

---

## 🎯 향후 개선 방향

### 단기
1. 🔄 **Task A.1**: 4단계 필터 체인 통합
   - HPF + Impulse Suppressor + AI + Limiter
   - RTF < 0.1 유지, 총성/폭발음 대응
1. 🔄 **Task B**: WiFi Direct 양방향 통신
2. 🔄 전장 환경 필드 테스트

### 중장기
1. **Task A.2**: Light-40 모델 재훈련 (음성 왜곡 해결)
2. **Task A.3**: 전장 소음 데이터 증강 (헬기/총성 학습)
3. Echo cancellation 추가
4. 적응형 비트레이트 제어


---

## 📅 프로젝트 타임라인

```
2025-09 ~ 2025-10: Phase 1-6 완료 (모델 훈련 및 실시간 구동)
2025-10-22: Phase 6.5 완료 (원본 모델 테스트) ⬅️ 현재
2025-10-23: Task A.1 시작 (4단계 필터 체인)
2025-10-23: Task C 진행 예정 (WiFi 통신)
2025-10-24: 통합 및 테스트
2025-11: Task A.2-A.3 진행 예정 (모델 업그레이드 + 데이터 증강)
```

---

## 📜 라이선스

이 프로젝트는 [Facebook Research Denoiser](https://github.com/facebookresearch/denoiser)를 기반으로 합니다.

---

## 🔗 참고 자료

### 공식 문서

- [Facebook Research Denoiser](https://github.com/facebookresearch/denoiser)
- [PyTorch Documentation](https://pytorch.org/docs/stable/index.html)
- [sounddevice Documentation](https://python-sounddevice.readthedocs.io/)
- [Hydra Documentation](https://hydra.cc/docs/intro/)

### 기술 참고

- [Opus Codec](https://opus-codec.org/)
- [WiFi Direct on Linux](https://wireless.wiki.kernel.org/en/users/Documentation/hostapd)
- [Real Time Speech Enhancement in the Waveform Domain (Paper)](https://arxiv.org/abs/2006.12847)

---

## ❓ FAQ
### Q: 원본 모델은 왜 실시간이 안되나요?

**A**: dns48/dns64는 파라미터가 43-77배 많아 RP5 CPU로는 RTF > 1.0

---

## 📝 버전 히스토리

| 버전       | 날짜             | 변경사항                          |
| -------- | -------------- | ----------------------------- |
| v1.0     | 2025-01-08     | 초기 계획                         |
| v2.0     | 2025-01-09     | RTF 최적화 완료                    |
| v3.0     | 2025-01-10     | Migration 완료                  |
| v4.1     | 2025-01-11     | 간결화 (클로드 가독성 중심)              |
| v4.2     | 2025-01-13     | Phase 3 완료, Phase 4 준비        |
| **v5.0** | **2025-01-23** | **Phase 6.5 완료, Task A/C 추가** |
| **v5.1** | **2025-01-24** | **Task A 계획 수정 (6단계→4단계)**    |
**v5.0 주요 변경**:
- Phase 6 실시간 스트리밍 구현 완료 (RTF 0.071)
- Phase 6.5 원본 모델 테스트 완료 (dns48/dns64 비교)
- Task A (필터 체인) 계획 추가
- Task C (WiFi 통신) 계획 추가
- 하드웨어 환경 상세 명시
- Troubleshooting 섹션 추가
**v5.1 주요 변경**:
- Task A 단순화: 6단계 → 4단계 필터 시스템
- 실제 문제점 명시 (음성 왜곡, 총성, 헬기)
- Phase A.1 (즉시) / A.2-A.3 (향후) 분리
- Light-40 재훈련 계획 추

---

## 기여

이 프로젝트는 군 통신 개선을 위한 연구 프로젝트입니다.

**Contact**: David(박성민) & Claude

---

**Last Updated**: 2025-01-23  
**Status**: Phase 6.5 완료, Task A 준비 중  
**Git Commit**: cf731606