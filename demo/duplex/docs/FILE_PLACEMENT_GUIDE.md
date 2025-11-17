# RP5 Full-Duplex 모듈화 - 파일 배치 가이드

## 📁 최종 디렉토리 구조

```
Facebook-Denoiser-in-Raspberry-Pi-5/
└── demo/
    └── duplex/
        ├── core/                           # 🆕 새 디렉토리
        │   ├── __init__.py                 # 파일 1
        │   ├── audio_processor.py          # 파일 2
        │   └── audio_comm.py               # 파일 3
        │
        ├── processors/                     # 🆕 새 디렉토리
        │   ├── __init__.py                 # 파일 4 (다른 __init__.py!)
        │   ├── bypass.py                   # 파일 5
        │   ├── ai_denoiser.py              # 파일 6
        │   └── classical_filters.py        # 파일 7
        │
        ├── configs/
        │   ├── rp5a_modular.yaml           # 파일 8
        │   └── rp5b_modular.yaml           # 파일 9
        │
        ├── rp5_full_duplex_modular.py      # 파일 10 (메인)
        ├── SUCCESSFUL_SETUP_RECORD.md      # 파일 11
        ├── MODULAR_ARCHITECTURE.md         # 파일 12
        └── MODULAR_INSTALLATION_GUIDE.md   # 파일 13
```

---

## 🔗 파일별 상세 위치 및 링크

### 1. Core 모듈 (3개 파일)

#### 📄 core/__init__.py
**최종 위치**: `demo/duplex/core/__init__.py`
**Outputs 링크**: [core/__init__.py](computer:///mnt/user-data/outputs/core/__init__.py)
**내용**: Core 모듈 초기화
```python
from .audio_processor import AudioProcessor
from .audio_comm import AudioComm
```

---

#### 📄 core/audio_processor.py
**최종 위치**: `demo/duplex/core/audio_processor.py`
**Outputs 링크**: [core/audio_processor.py](computer:///mnt/user-data/outputs/core/audio_processor.py)
**내용**: 오디오 프로세서 추상 베이스 클래스

---

#### 📄 core/audio_comm.py
**최종 위치**: `demo/duplex/core/audio_comm.py`
**Outputs 링크**: [core/audio_comm.py](computer:///mnt/user-data/outputs/core/audio_comm.py)
**내용**: UDP 통신, Opus 코덱, Resampling

---

### 2. Processors 모듈 (4개 파일)

#### 📄 processors/__init__.py (⚠️ 다른 __init__.py!)
**최종 위치**: `demo/duplex/processors/__init__.py`
**Outputs 링크**: [processors/__init__.py](computer:///mnt/user-data/outputs/processors/__init__.py)
**내용**: Processors 모듈 초기화
```python
from .bypass import BypassProcessor
from .ai_denoiser import AIDenoiserProcessor
from .classical_filters import ClassicalFiltersProcessor
```

---

#### 📄 processors/bypass.py
**최종 위치**: `demo/duplex/processors/bypass.py`
**Outputs 링크**: [processors/bypass.py](computer:///mnt/user-data/outputs/processors/bypass.py)
**내용**: Bypass 프로세서 (처리 없음)

---

#### 📄 processors/ai_denoiser.py
**최종 위치**: `demo/duplex/processors/ai_denoiser.py`
**Outputs 링크**: [processors/ai_denoiser.py](computer:///mnt/user-data/outputs/processors/ai_denoiser.py)
**내용**: AI 디노이징 프로세서

---

#### 📄 processors/classical_filters.py
**최종 위치**: `demo/duplex/processors/classical_filters.py`
**Outputs 링크**: [processors/classical_filters.py](computer:///mnt/user-data/outputs/processors/classical_filters.py)
**내용**: 고전적 필터 프로세서 (stub)

---

### 3. 메인 애플리케이션 (1개 파일)

#### 📄 rp5_full_duplex_modular.py
**최종 위치**: `demo/duplex/rp5_full_duplex_modular.py`
**Outputs 링크**: [rp5_full_duplex_modular.py](computer:///mnt/user-data/outputs/rp5_full_duplex_modular.py)
**내용**: 메인 애플리케이션 (토글 지원)

---

### 4. 설정 파일 (2개 파일)

#### 📄 rp5a_modular.yaml
**최종 위치**: `demo/duplex/configs/rp5a_modular.yaml`
**Outputs 링크**: [rp5a_modular.yaml](computer:///mnt/user-data/outputs/rp5a_modular.yaml)
**내용**: RP5-A 설정 (버퍼 10)

---

#### 📄 rp5b_modular.yaml
**최종 위치**: `demo/duplex/configs/rp5b_modular.yaml`
**Outputs 링크**: [rp5b_modular.yaml](computer:///mnt/user-data/outputs/rp5b_modular.yaml)
**내용**: RP5-B 설정 (버퍼 5)

---

### 5. 문서 (3개 파일)

#### 📄 SUCCESSFUL_SETUP_RECORD.md
**최종 위치**: `demo/duplex/SUCCESSFUL_SETUP_RECORD.md`
**Outputs 링크**: [SUCCESSFUL_SETUP_RECORD.md](computer:///mnt/user-data/outputs/SUCCESSFUL_SETUP_RECORD.md)
**내용**: 성공한 세팅 기록

---

#### 📄 MODULAR_ARCHITECTURE.md
**최종 위치**: `demo/duplex/MODULAR_ARCHITECTURE.md`
**Outputs 링크**: [MODULAR_ARCHITECTURE.md](computer:///mnt/user-data/outputs/MODULAR_ARCHITECTURE.md)
**내용**: 아키텍처 설계 문서

---

#### 📄 MODULAR_INSTALLATION_GUIDE.md
**최종 위치**: `demo/duplex/MODULAR_INSTALLATION_GUIDE.md`
**Outputs 링크**: [MODULAR_INSTALLATION_GUIDE.md](computer:///mnt/user-data/outputs/MODULAR_INSTALLATION_GUIDE.md)
**내용**: 종합 설치 가이드

---

## 🚀 빠른 설치 명령어

### Mac에서 한 번에 복사

```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5

# 1. 디렉토리 생성
mkdir -p demo/duplex/core
mkdir -p demo/duplex/processors

# 2. Core 모듈 (3개)
# ⚠️ 첫 번째 __init__.py는 core/로!
cp ~/Downloads/outputs/core/__init__.py demo/duplex/core/
cp ~/Downloads/outputs/core/audio_processor.py demo/duplex/core/
cp ~/Downloads/outputs/core/audio_comm.py demo/duplex/core/

# 3. Processors 모듈 (4개)
# ⚠️ 두 번째 __init__.py는 processors/로!
cp ~/Downloads/outputs/processors/__init__.py demo/duplex/processors/
cp ~/Downloads/outputs/processors/bypass.py demo/duplex/processors/
cp ~/Downloads/outputs/processors/ai_denoiser.py demo/duplex/processors/
cp ~/Downloads/outputs/processors/classical_filters.py demo/duplex/processors/

# 4. 메인 및 설정
cp ~/Downloads/outputs/rp5_full_duplex_modular.py demo/duplex/
cp ~/Downloads/outputs/rp5a_modular.yaml demo/duplex/configs/
cp ~/Downloads/outputs/rp5b_modular.yaml demo/duplex/configs/

# 5. 문서
cp ~/Downloads/outputs/SUCCESSFUL_SETUP_RECORD.md demo/duplex/
cp ~/Downloads/outputs/MODULAR_ARCHITECTURE.md demo/duplex/
cp ~/Downloads/outputs/MODULAR_INSTALLATION_GUIDE.md demo/duplex/

# 6. 확인
ls -la demo/duplex/core/
ls -la demo/duplex/processors/
ls demo/duplex/*.py
ls demo/duplex/configs/*_modular.yaml
```

---

## ✅ 설치 확인

### 디렉토리 구조 검증

```bash
# 예상 출력
tree demo/duplex/ -L 2

demo/duplex/
├── core/
│   ├── __init__.py          ✅
│   ├── audio_processor.py   ✅
│   └── audio_comm.py        ✅
├── processors/
│   ├── __init__.py          ✅ (다른 파일!)
│   ├── bypass.py            ✅
│   ├── ai_denoiser.py       ✅
│   └── classical_filters.py ✅
├── configs/
│   ├── rp5a_modular.yaml    ✅
│   └── rp5b_modular.yaml    ✅
├── rp5_full_duplex_modular.py ✅
└── *.md                       ✅ (3개 문서)
```

### 파일 개수 확인

```bash
# Core: 3개
ls demo/duplex/core/ | wc -l
# 예상: 3

# Processors: 4개
ls demo/duplex/processors/ | wc -l
# 예상: 4
```

---

## 🔍 __init__.py 구분 방법

### 방법 1: 내용으로 구분

**core/__init__.py의 내용:**
```python
from .audio_processor import AudioProcessor
from .audio_comm import AudioComm
```

**processors/__init__.py의 내용:**
```python
from .bypass import BypassProcessor
from .ai_denoiser import AIDenoiserProcessor
from .classical_filters import ClassicalFiltersProcessor
```

### 방법 2: 파일 크기로 구분

```bash
# core/__init__.py: 작음 (약 200 bytes)
# processors/__init__.py: 조금 더 큼 (약 300 bytes)

ls -lh ~/Downloads/outputs/core/__init__.py
ls -lh ~/Downloads/outputs/processors/__init__.py
```

---

## 🐛 문제 해결

### 문제: "No module named 'demo.duplex.core'"

**원인**: 디렉토리 구조 잘못됨

**확인**:
```bash
# 이 파일이 있어야 함
ls demo/duplex/core/__init__.py
ls demo/duplex/processors/__init__.py
```

**해결**: 위의 복사 명령어 다시 실행

---

### 문제: "cannot import name 'AudioProcessor'"

**원인**: 잘못된 __init__.py 배치

**확인**:
```bash
# core/__init__.py 내용 확인
cat demo/duplex/core/__init__.py
# "from .audio_processor import AudioProcessor" 있어야 함

# processors/__init__.py 내용 확인  
cat demo/duplex/processors/__init__.py
# "from .bypass import BypassProcessor" 있어야 함
```

**해결**: __init__.py 위치 교체

---

## 📝 체크리스트

복사 후 다음을 확인:

**디렉토리:**
- [ ] `demo/duplex/core/` 존재
- [ ] `demo/duplex/processors/` 존재

**Core (3개):**
- [ ] `demo/duplex/core/__init__.py`
- [ ] `demo/duplex/core/audio_processor.py`
- [ ] `demo/duplex/core/audio_comm.py`

**Processors (4개):**
- [ ] `demo/duplex/processors/__init__.py`
- [ ] `demo/duplex/processors/bypass.py`
- [ ] `demo/duplex/processors/ai_denoiser.py`
- [ ] `demo/duplex/processors/classical_filters.py`

**메인 (1개):**
- [ ] `demo/duplex/rp5_full_duplex_modular.py`

**설정 (2개):**
- [ ] `demo/duplex/configs/rp5a_modular.yaml`
- [ ] `demo/duplex/configs/rp5b_modular.yaml`

**문서 (3개):**
- [ ] `demo/duplex/SUCCESSFUL_SETUP_RECORD.md`
- [ ] `demo/duplex/MODULAR_ARCHITECTURE.md`
- [ ] `demo/duplex/MODULAR_INSTALLATION_GUIDE.md`

---

## 💡 참고

**__init__.py 파일 역할:**
- Python 패키지로 인식시키기
- 모듈 import 단순화
- 각 디렉토리마다 다른 내용!

**경로 구분:**
- `core/__init__.py` → Core 모듈용
- `processors/__init__.py` → Processors 모듈용

---

**작성**: 2025-11-14
**목적**: 파일 배치 혼란 해소
