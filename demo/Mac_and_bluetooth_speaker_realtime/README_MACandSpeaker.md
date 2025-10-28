# Mac & Bluetooth Speaker Realtime Demo

Mac에서 블루투스 스피커로 실시간 음성 디노이징을 시연하기 위한 스크립트

## 📁 파일 구조
```
Mac_and_bluetooth_speaker_realtime/
├── mac_realtime.py           # 실시간 데모 메인 스크립트
├── download_fair_model.py    # Facebook 사전훈련 모델 다운로드
└── README.md                 # 이 파일
```

## 🎯 목적

- **시연 환경**: Mac → Bluetooth Speaker (직접 연결)
- **특징**: 
  - 낮은 지연시간 (~50-100ms)
  - Facebook 최고 사양 모델 사용
  - Enter 키로 실시간 ON/OFF 토글

## 🚀 사용법

### 1. 사전 준비
```bash
# 1) Conda 환경 활성화
conda activate denoiser_modern

# 2) PyAudio 설치 (최초 1회)
brew install portaudio
pip install pyaudio

# 3) 블루투스 스피커 페어링
# Mac 시스템 설정 → 블루투스 → 스피커 연결
```

### 2. 모델 다운로드 (최초 1회)
```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5

python demo/Mac_and_bluetooth_speaker_realtime/download_fair_model.py
```

**다운로드되는 모델**:
- `models/dns64.th` (~128MB) - Facebook DNS64 (최고 사양)
- `models/dns48.th` (~75MB) - Facebook DNS48 (고사양)  
- `models/master64.th` (~128MB) - Valentini 사전훈련

### 3. 실시간 데모 실행
```bash
python demo/Mac_and_bluetooth_speaker_realtime/mac_realtime.py
```

### 4. 실행 과정
```
Step 1: 모델 선택
==================================================
🤖 Available Models:
==================================================
[1] ✅ Facebook DNS64 (hidden=64, depth=5) - 최고 사양
[2] ✅ Facebook DNS48 (hidden=48, depth=5) - 고사양
[3] ✅ Facebook Master64 (hidden=64, depth=5) - Valentini 사전훈련
[4] ✅ Custom Light32 (hidden=32, depth=4) - RP5 최적화
==================================================
Select model number: 1

Step 2: 입력 디바이스 선택 (마이크)
==================================================
🎤 Available Input Devices:
==================================================
[0] AirPods
[2] MacBook Pro 마이크
==================================================
Select INPUT device number: 0

Step 3: 출력 디바이스 선택 (스피커)
==================================================
🔊 Available Output Devices:
==================================================
[1] AirPods
[3] MacBook Pro 스피커
  └─ 🔵 Bluetooth device detected!
==================================================
Select OUTPUT device number: 1

Step 4: 실시간 처리 시작
==================================================
🎛️  Controls:
==================================================
  Enter       : Toggle denoising ON/OFF
  'q' + Enter : Quit
==================================================
🎙️  Recording started... (Press Enter to toggle)

[Enter] → 🔴 OFF (원본 음성)
[Enter] → 🟢 ON (디노이징 적용)
[q + Enter] → 종료
```

## 📊 모델 선택 가이드

| 모델 | 파라미터 | 크기 | RTF (Mac) | 추천 용도 |
|------|---------|------|-----------|----------|
| **dns64** | hidden=64, depth=5 | 128MB | < 0.1 | **시연용 (최고 품질)** |
| dns48 | hidden=48, depth=5 | 75MB | < 0.08 | 균형잡힌 선택 |
| master64 | hidden=64, depth=5 | 128MB | < 0.1 | Valentini 최적화 |
| light32 | hidden=32, depth=4 | 2MB | 0.834 (RP5) | RP5 배포용 |

**시연 추천**: dns64 (최고 품질)

## 🔧 연결 방식 비교

### ✅ 현재 방식: Mac → Bluetooth Speaker
```
[마이크] → [Mac 디노이징] → [Bluetooth] → [스피커]
         ↑________________↑
         (실시간 처리)
```

**장점**:
- 낮은 지연시간 (~50-100ms)
- 네트워크 홉 최소화
- 안정적인 연결

**단점**:
- Mac의 입출력을 동시 처리

### ❌ 대안 (비추천): Mac → RP5 → Bluetooth Speaker
```
[마이크] → [Mac] → [WiFi] → [RP5] → [Bluetooth] → [스피커]
                   ↑_____________↑
                   (추가 지연)
```

**단점**:
- 지연시간 증가 (80-350ms) - 사람이 인지 가능
- WiFi 패킷 로스 가능성
- 복잡한 구조

## ⚠️ 문제 해결

### 1. "ModuleNotFoundError: No module named 'denoiser'"
```bash
# 경로 문제 - 프로젝트 루트에서 실행
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5
python demo/Mac_and_bluetooth_speaker_realtime/mac_realtime.py
```

### 2. "No module named 'pyaudio'"
```bash
conda activate denoiser_modern
brew install portaudio
pip install pyaudio
```

### 3. 블루투스 스피커가 목록에 없음

- Mac 시스템 설정 → 블루투스에서 먼저 연결
- 연결 후 스크립트 재실행

### 4. 오디오가 끊김 / 지연 발생

**방법 1**: CHUNK_SIZE 조정 (mac_realtime.py 25번째 줄)
```python
CHUNK_SIZE = 1024  # 기본 512 → 1024로 증가
```

**방법 2**: 더 가벼운 모델 선택
- dns64 → dns48 또는 light32

### 5. 모델 로딩 실패
```bash
# 모델 재다운로드
rm models/dns64.th
python demo/Mac_and_bluetooth_speaker_realtime/download_fair_model.py
```

## 🎓 시연 팁

### 1. 시연 전 체크리스트

- [ ] 블루투스 스피커 페어링 완료
- [ ] `dns64.th` 모델 다운로드 완료 (128MB)
- [ ] 조용한 환경 확보 (노이즈 효과 극대화)
- [ ] 백업 스피커 준비 (만약을 위해)

### 2. 시연 시나리오
```
1. 스크립트 실행 → dns64 선택
2. 디노이징 OFF 상태로 시작 (🔴)
   → "이것이 원본 음성입니다" (노이즈 들림)
3. Enter 키 → 디노이징 ON (🟢)
   → "이제 노이즈가 제거되었습니다" (깨끗한 음성)
4. 몇 번 토글하며 차이 강조
```

### 3. 노이즈 테스트 방법

- 키보드 타이핑 소리
- 종이 구기는 소리
- 배경 음악 재생
- 에어컨/선풍기 소음

## 📖 참고 자료

- **Facebook Denoiser 원본**: https://github.com/facebookresearch/denoiser
- **논문**: Real Time Speech Enhancement in the Waveform Domain (https://arxiv.org/abs/2006.12847)
- **프로젝트 GitHub**: https://github.com/sungmin-park-dev/Facebook-Denoiser-in-Raspberry-Pi-5

## 🔄 관련 파일

- **훈련 코드**: `denoiser/`
- **설정 파일**: `conf/`
- **RP5 최적화**: `rpi5_optimization/`
- **모델 저장**: `models/`

## 📝 버전 이력

- **v1.0** (2025-10-28): 초기 버전
  - Facebook 모델 3종 지원
  - Enter 토글 기능
  - 블루투스 스피커 자동 감지

---

**작성자**: David  
**최종 업데이트**: 2025-10-28  
**환경**: macOS, Python 3.12, PyTorch 2.8.0