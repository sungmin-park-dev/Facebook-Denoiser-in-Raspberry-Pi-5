# RP5 Full-Duplex 모듈화 아키텍처

## 🎯 설계 목표

1. **통신 로직 분리**: UDP, Opus, Resample → 독립 모듈
2. **오디오 처리 플러그인**: AI, 고전적 필터 등 교체 가능
3. **토글 시스템**: 런타임에 프로세서 전환
4. **유지보수성**: 기능별 파일 분리

---

## 📁 파일 구조

```
demo/duplex/
├── core/
│   ├── __init__.py
│   ├── audio_comm.py          # 통신 담당 (UDP, Opus, Resample)
│   └── audio_processor.py     # 오디오 처리 인터페이스 (Abstract Base)
│
├── processors/
│   ├── __init__.py
│   ├── bypass.py              # 처리 없음 (Passthrough)
│   ├── ai_denoiser.py         # AI 디노이징 (Light-32-Depth4)
│   └── classical_filters.py   # 고전적 필터 (추후 구현)
│
├── rp5_full_duplex_modular.py # 메인 (토글 지원)
├── start_modular_a.py          # RP5-A 실행 스크립트
├── start_modular_b.py          # RP5-B 실행 스크립트
│
└── configs/
    ├── rp5a_modular.yaml       # A 설정 (버퍼 증가)
    └── rp5b_modular.yaml       # B 설정
```

---

## 🔧 모듈 상세

### 1. core/audio_comm.py

**책임**: 순수 오디오 통신
- UDP 송수신
- Opus 인코딩/디코딩
- 48kHz ↔ 16kHz Resampling
- Queue 관리

**인터페이스**:
```python
class AudioComm:
    def __init__(self, role, peer_ip, ports, buffer_size=5):
        pass
    
    def send(self, audio_16k: np.ndarray) -> None:
        """16kHz audio → Encode → UDP send"""
        pass
    
    def receive(self) -> np.ndarray:
        """UDP receive → Decode → 16kHz audio"""
        pass
```

---

### 2. core/audio_processor.py

**책임**: 오디오 처리 인터페이스
- Abstract Base Class
- 모든 프로세서의 공통 인터페이스

**인터페이스**:
```python
from abc import ABC, abstractmethod

class AudioProcessor(ABC):
    """Base class for all audio processors"""
    
    @abstractmethod
    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        Process audio (16kHz, mono, float32)
        
        Args:
            audio: Input audio [-1.0, 1.0]
        
        Returns:
            Processed audio [-1.0, 1.0]
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return processor name for display"""
        pass
```

---

### 3. processors/bypass.py

**책임**: 처리 없음 (Direct passthrough)

```python
class BypassProcessor(AudioProcessor):
    def process(self, audio: np.ndarray) -> np.ndarray:
        return audio
    
    def get_name(self) -> str:
        return "Bypass (No Processing)"
```

---

### 4. processors/ai_denoiser.py

**책임**: AI 디노이징

```python
class AIDenoiserProcessor(AudioProcessor):
    def __init__(self, model_name="Light-32-Depth4"):
        self.denoiser = ModelLoader.load(model_name)
        self.denoiser.eval()
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            tensor = torch.from_numpy(audio).float().unsqueeze(0).unsqueeze(0)
            denoised = self.denoiser(tensor)
            return denoised.squeeze().cpu().numpy()
    
    def get_name(self) -> str:
        return "AI Denoiser (Light-32-Depth4)"
```

---

### 5. processors/classical_filters.py

**책임**: 고전적 필터 (추후 구현)

```python
class ClassicalFiltersProcessor(AudioProcessor):
    """
    Classical noise reduction methods:
    - Phase inversion
    - Blind Source Separation (BSS)
    - Frequency filtering
    - Amplitude filtering
    """
    
    def __init__(self, config):
        # TODO: Load filter config
        pass
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        # TODO: Apply classical filters
        return audio
    
    def get_name(self) -> str:
        return "Classical Filters (Phase/BSS/Freq/Amp)"
```

---

### 6. rp5_full_duplex_modular.py

**책임**: 메인 애플리케이션
- AudioComm + AudioProcessor 조합
- 토글 시스템 (Enter로 프로세서 전환)
- Stats 출력

**구조**:
```python
class FullDuplexModular:
    def __init__(self, comm, processors, initial_processor=0):
        self.comm = comm
        self.processors = processors  # List[AudioProcessor]
        self.current_idx = initial_processor
    
    def send_thread(self):
        while running:
            audio_48k = mic_queue.get()
            audio_16k = downsample(audio_48k)
            
            # 현재 활성 프로세서로 처리
            processed = self.processors[self.current_idx].process(audio_16k)
            
            self.comm.send(processed)
    
    def recv_thread(self):
        while running:
            audio_16k = self.comm.receive()
            audio_48k = upsample(audio_16k)
            speaker_queue.put(audio_48k)
    
    def toggle_processor(self):
        """Enter 키로 프로세서 전환"""
        self.current_idx = (self.current_idx + 1) % len(self.processors)
        print(f"🔄 Switched to: {self.processors[self.current_idx].get_name()}")
```

---

## 🎛️ 토글 시스템

### 프로세서 전환 흐름

```
초기: Bypass (처리 없음)
  ↓ [Enter]
AI Denoiser (Light-32-Depth4)
  ↓ [Enter]
Classical Filters (Phase/BSS/Freq/Amp)
  ↓ [Enter]
Bypass (처리 없음)  ← 순환
```

### 사용자 인터페이스

```
🎛️  Press Enter to toggle processor, 'q' + Enter to quit
Current: Bypass (No Processing)

[Enter 입력]
🔄 Switched to: AI Denoiser (Light-32-Depth4)

[Enter 입력]
🔄 Switched to: Classical Filters (Phase/BSS/Freq/Amp)
```

---

## 🔧 RP5-A 끊김 해결 방안

### 문제 분석
- **증상**: Hotspot 호스트(test1)에서 송신 시 끊김
- **원인**: AP 운영 + 오디오 처리의 CPU 부하

### 해결 방법

#### 1. 버퍼 크기 증가 (test1 전용)
```yaml
# rp5a_modular.yaml
buffer_size: 10  # 5 → 10 (test1만)
```

#### 2. 스레드 우선순위 조정
```python
import os
# 오디오 스레드 우선순위 높임
os.nice(-10)  # Requires sudo or CAP_SYS_NICE
```

#### 3. CPU Governor 설정
```bash
# RP5-A에서 performance 모드
sudo cpupower frequency-set -g performance
```

#### 4. Chunk 크기 조정 (선택)
```python
# 더 큰 chunk = 덜 빈번한 처리
self.chunk_size_48k = 1920  # 40ms (vs 20ms)
```

---

## 📊 설정 비교

| 설정 | RP5-A (Hotspot) | RP5-B (Client) |
|------|-----------------|----------------|
| **Buffer Size** | 10 frames | 5 frames |
| **Thread Priority** | High (-10) | Normal (0) |
| **CPU Governor** | performance | ondemand |
| **Chunk Size** | 960 (20ms) | 960 (20ms) |

---

## 🚀 마이그레이션 경로

### Phase 1: 모듈 생성 (현재)
- [ ] core/audio_comm.py
- [ ] core/audio_processor.py
- [ ] processors/bypass.py
- [ ] processors/ai_denoiser.py
- [ ] processors/classical_filters.py (stub)

### Phase 2: 메인 통합
- [ ] rp5_full_duplex_modular.py
- [ ] 토글 시스템 구현
- [ ] RP5-A 버퍼 최적화

### Phase 3: 테스트
- [ ] Bypass 모드 검증
- [ ] AI 모드 검증
- [ ] 토글 전환 검증
- [ ] RP5-A 끊김 개선 확인

### Phase 4: 기존 파일 대체
- [ ] start_full_duplex_a.py → start_modular_a.py
- [ ] 설정 파일 업데이트
- [ ] 문서 업데이트

---

## 💡 추가 고려사항

### 오디오 디바이스 독립 선택
```python
# 향후: 마이크와 스피커 분리 선택
AudioComm(
    mic_device=2,      # 별도 마이크
    speaker_device=5   # 블루투스 스피커
)
```

### 블루투스 Latency 보상
```python
# 블루투스 스피커 사용 시 추가 latency 고려
if is_bluetooth_speaker:
    buffer_size += 5  # 추가 버퍼링
```

### 프로세서 체인 (향후)
```python
# 여러 프로세서 순차 적용
processors = [
    HighPassFilter(),
    AIDenoiser(),
    Limiter()
]
```

---

**설계일**: 2025-11-14
**목표**: 유지보수 용이한 모듈화 아키텍처
