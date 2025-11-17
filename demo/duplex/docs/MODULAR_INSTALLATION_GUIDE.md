# RP5 Full-Duplex 모듈화 버전 - 종합 가이드

## 🎯 개요

**새 기능:**
- ✅ 통신과 오디오 처리 완전 분리
- ✅ 런타임 프로세서 토글 (Enter 키)
- ✅ RP5-A 끊김 해결 (버퍼 증가)
- ✅ 향후 확장 용이 (필터 추가 간편)

---

## 📁 파일 구조

```
demo/duplex/
├── core/
│   ├── __init__.py
│   ├── audio_comm.py          # UDP, Opus, Resample
│   └── audio_processor.py     # Base class
│
├── processors/
│   ├── __init__.py
│   ├── bypass.py              # No processing
│   ├── ai_denoiser.py         # AI denoising
│   └── classical_filters.py   # Classical (TBD)
│
├── rp5_full_duplex_modular.py # 메인
├── configs/
│   ├── rp5a_modular.yaml      # A 설정 (버퍼 10)
│   └── rp5b_modular.yaml      # B 설정 (버퍼 5)
│
└── [기존 파일들 유지]
```

---

## 📦 설치 방법

### Step 1: Mac에서 파일 복사

```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5

# 디렉토리 생성
mkdir -p demo/duplex/core
mkdir -p demo/duplex/processors

# Core 모듈
cp /path/to/outputs/core/__init__.py demo/duplex/core/
cp /path/to/outputs/core/audio_processor.py demo/duplex/core/
cp /path/to/outputs/core/audio_comm.py demo/duplex/core/

# Processors
cp /path/to/outputs/processors/__init__.py demo/duplex/processors/
cp /path/to/outputs/processors/bypass.py demo/duplex/processors/
cp /path/to/outputs/processors/ai_denoiser.py demo/duplex/processors/
cp /path/to/outputs/processors/classical_filters.py demo/duplex/processors/

# 메인 및 설정
cp /path/to/outputs/rp5_full_duplex_modular.py demo/duplex/
cp /path/to/outputs/rp5a_modular.yaml demo/duplex/configs/
cp /path/to/outputs/rp5b_modular.yaml demo/duplex/configs/

# 문서
cp /path/to/outputs/SUCCESSFUL_SETUP_RECORD.md demo/duplex/
cp /path/to/outputs/MODULAR_ARCHITECTURE.md demo/duplex/
```

### Step 2: Git 커밋

```bash
git add demo/duplex/core/
git add demo/duplex/processors/
git add demo/duplex/rp5_full_duplex_modular.py
git add demo/duplex/configs/*_modular.yaml
git add demo/duplex/*.md

git commit -m "Add: Modular architecture for full-duplex communication

- Separate communication (core/audio_comm.py) and processing (processors/)
- Pluggable audio processors with runtime toggle support
- RP5-A buffer increased (10) to reduce dropout
- Processors: Bypass, AI Denoiser, Classical (stub)
- Easy to add new processors in the future"

git push origin main
```

### Step 3: RP5에 배포

```bash
# RP5-A
cd /home/test1/denoiser
git pull origin main

# RP5-B
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
git pull origin main
```

---

## 🚀 사용 방법

### RP5-A 실행

```bash
cd /home/test1/denoiser
source venv/bin/activate

python demo/duplex/rp5_full_duplex_modular.py \
    --config demo/duplex/configs/rp5a_modular.yaml
```

### RP5-B 실행

```bash
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
source venv_denoiser/bin/activate

python demo/duplex/rp5_full_duplex_modular.py \
    --config demo/duplex/configs/rp5b_modular.yaml
```

---

## 🎛️ 토글 사용법

### 프로세서 전환

실행 중 **Enter 키** 누르면 프로세서 순환:

```
초기: [0] Bypass (No Processing)
  ↓ [Enter]
[1] AI Denoiser (Light-32-Depth4)
  ↓ [Enter]
[2] Classical Filters (TBD)
  ↓ [Enter]
[0] Bypass (순환)
```

### 종료

`q` + `Enter` 입력

---

## 🔧 RP5-A 끊김 해결

### 적용된 해결책

**1. 버퍼 증가**
```yaml
# rp5a_modular.yaml
buffer_size: 10  # 5 → 10
```

**2. 추가 최적화 (선택사항)**

```bash
# RP5-A에서 CPU performance 모드
sudo cpupower frequency-set -g performance

# 확인
cpupower frequency-info
```

**3. 스레드 우선순위 (향후 구현)**
```python
# rp5_full_duplex_modular.py에 추가 예정
import os
os.nice(-10)  # Requires sudo
```

---

## 📊 설정 비교

| 항목 | RP5-A (Hotspot) | RP5-B (Client) | 이유 |
|------|-----------------|----------------|------|
| buffer_size | 10 | 5 | AP overhead |
| CPU governor | performance | ondemand | 안정성 |
| 우선순위 | 높음 | 보통 | 끊김 방지 |

---

## 🆕 새 프로세서 추가 방법

### 1. 프로세서 클래스 생성

```python
# demo/duplex/processors/my_filter.py

from demo.duplex.core.audio_processor import AudioProcessor

class MyFilterProcessor(AudioProcessor):
    def process(self, audio):
        # 처리 로직
        return filtered_audio
    
    def get_name(self):
        return "My Custom Filter"
```

### 2. __init__.py에 추가

```python
# demo/duplex/processors/__init__.py

from .my_filter import MyFilterProcessor

__all__ = [..., 'MyFilterProcessor']
```

### 3. 설정 파일에서 활성화

```yaml
# configs/rp5a_modular.yaml
enable_my_filter: true
```

### 4. 메인 파일에서 로드

```python
# rp5_full_duplex_modular.py

if config.get('enable_my_filter', False):
    processors.append(MyFilterProcessor())
```

---

## 🎯 향후 계획

### Phase 1: 고전적 필터 구현
- [ ] High-pass filter (80Hz)
- [ ] Phase inversion (역위상)
- [ ] BSS (Blind Source Separation)
- [ ] Spectral subtraction
- [ ] Wiener filtering

### Phase 2: 오디오 디바이스 독립 선택
```yaml
# 향후 설정
mic_device: 2      # 별도 마이크
speaker_device: 5  # 블루투스 스피커
```

### Phase 3: 프로세서 체인
```python
# 여러 프로세서 순차 적용
processors = [
    HighPassFilter(),
    AIDenoiser(),
    Limiter()
]
```

---

## 🐛 문제 해결

### 문제 1: "No module named 'demo.duplex.core'"

**원인**: Python path 문제

**해결**:
```bash
cd /path/to/Facebook-Denoiser-in-Raspberry-Pi-5
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python demo/duplex/rp5_full_duplex_modular.py --config ...
```

### 문제 2: RP5-A 여전히 끊김

**진단**:
```bash
# CPU 사용률 확인
htop

# 네트워크 확인
iftop -i p2p-dev-wlan0
```

**추가 조치**:
1. buffer_size 더 증가 (15-20)
2. chunk_size 증가 (960 → 1920)
3. WiFi channel 변경

### 문제 3: AI 모델 로드 실패

**확인**:
```bash
ls models/current/best.th
```

**해결**:
```bash
# 모델 다운로드 또는 복사
cp /path/to/best.th models/current/
```

---

## 📈 성능 비교

| 모드 | Latency | CPU 사용 | 음질 | 비고 |
|------|---------|---------|------|------|
| Bypass | ~500ms | 낮음 | Raw | 통신만 |
| AI Denoiser | ~550ms | 중간 | 우수 | RTF 0.07 |
| Classical | TBD | TBD | TBD | 미구현 |

---

## ✅ 검증 체크리스트

### 기본 기능
- [ ] RP5-A, RP5-B 모두 시작됨
- [ ] 양방향 소리 들림
- [ ] TX/RX 패킷 수 증가
- [ ] 에러 없음

### 토글 기능
- [ ] Enter 키로 프로세서 전환
- [ ] 화면에 현재 프로세서 표시
- [ ] Bypass → AI 전환 시 소리 변화 감지
- [ ] AI → Bypass 전환 시 원음 복원

### RP5-A 끊김
- [ ] Bypass 모드에서 끊김 없음
- [ ] AI 모드에서도 끊김 감소
- [ ] 버퍼 증가 효과 확인

---

## 📚 관련 문서

- [SUCCESSFUL_SETUP_RECORD.md](SUCCESSFUL_SETUP_RECORD.md) - 성공한 세팅 기록
- [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md) - 아키텍처 상세
- [DEBUG_USAGE_GUIDE.md](DEBUG_USAGE_GUIDE.md) - DEBUG 버전 가이드

---

**작성**: 2025-11-14
**버전**: v1.0
**상태**: ✅ Ready for deployment
