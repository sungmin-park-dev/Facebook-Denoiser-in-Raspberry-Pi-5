# Phase 2: RP5-A ↔ RP5-B Preparation Checklist

## 🎯 목표
라우터 없이 RP5 간 직접 WiFi 연결 및 양방향 음성 통신

---

## 📋 RP5-B 준비사항

### 1. 하드웨어 확인
- [ ] RP5-B Ubuntu 24.04 설치 완료
- [ ] WiFi 모듈 작동 확인: `ip link show wlan0`
- [ ] 오디오 디바이스 준비 (H08A 또는 블루투스)
- [ ] 전원 공급 안정성 확인

### 2. 기본 소프트웨어 설치
```bash
# RP5-B에서 실행
sudo apt update
sudo apt upgrade -y

# 필수 패키지
sudo apt install -y python3-venv python3-pip git

# 네트워크 도구
sudo apt install -y network-manager
```

### 3. 프로젝트 코드 배포
```bash
# RP5-B에서 실행
cd /home/test1
git clone https://github.com/sungmin-park-dev/Facebook-Denoiser-in-Raspberry-Pi-5.git denoiser
cd denoiser

# 가상환경 생성
python3 -m venv ~/venv
source ~/venv/bin/activate

# 의존성 설치
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install sounddevice numpy scipy opuslib

# Opus 라이브러리
sudo apt-get install -y libopus0 libopus-dev
```

### 4. 모델 파일 복사
**Option A: GitHub LFS (대용량 파일)**
```bash
# RP5-A에서 scp로 전송
scp models/current/best.th test1@[RP5-B IP]:/home/test1/denoiser/models/current/
```

**Option B: USB 드라이브**
- RP5-A에서 USB에 `models/current/best.th` 복사
- RP5-B에 USB 연결 후 복사

### 5. 테스트 실행
```bash
# RP5-B에서
cd /home/test1/denoiser
source ~/venv/bin/activate

# 오디오 디바이스 확인
python scripts/rp5_receiver.py --list-devices

# 코덱 테스트
python src/communication/codec.py
```

---

## 🌐 WiFi Direct 설정

### RP5-A: Access Point 모드
```bash
# WiFi AP 생성
sudo nmcli device wifi hotspot \
  ssid "TacticalComm" \
  password "secure12345" \
  ifname wlan0

# IP 확인 (보통 192.168.4.1)
ip addr show wlan0
```

### RP5-B: Client 모드
```bash
# AP에 연결
sudo nmcli device wifi connect "TacticalComm" password "secure12345"

# IP 확인 (DHCP 자동 할당, 보통 192.168.4.2)
ip addr show wlan0

# 연결 테스트
ping 192.168.4.1
```

---

## 🧪 Phase 2 테스트 시나리오

### Test 1: RP5-A → RP5-B (단방향)
```bash
# RP5-B (수신기)
python scripts/rp5_receiver.py --port 5000 --device [DEVICE_ID]

# RP5-A (송신기) - 스크립트 수정 필요
python scripts/rp5_sender.py --target-ip 192.168.4.2 --port 5000
```

### Test 2: RP5-B → RP5-A (역방향)
```bash
# RP5-A (수신기)
python scripts/rp5_receiver.py --port 5001 --device [DEVICE_ID]

# RP5-B (송신기)
python scripts/rp5_sender.py --target-ip 192.168.4.1 --port 5001
```

### Test 3: Full-Duplex (양방향 동시)
```bash
# RP5-A
python scripts/rp5_full_duplex.py --role A

# RP5-B
python scripts/rp5_full_duplex.py --role B
```

---

## 📝 필요한 새 스크립트

### 1. `scripts/rp5_sender.py`
- RP5에서 마이크 입력 → AI 디노이징 → UDP 송신
- `mac_sender.py`를 RP5용으로 수정

### 2. `scripts/rp5_full_duplex.py`
- 송신 + 수신 동시 실행
- 멀티스레드 구조

---

## ⏱️ 예상 소요 시간

| 작업 | 소요 시간 |
|------|----------|
| RP5-B 기본 설정 | 30분 |
| 프로젝트 코드 배포 | 20분 |
| WiFi Direct 설정 | 10분 |
| 단방향 테스트 (A→B) | 1시간 |
| 단방향 테스트 (B→A) | 30분 |
| Full-Duplex 구현 | 2시간 |
| 통합 테스트 | 1시간 |
| **총 예상 시간** | **약 5-6시간** |

---

## 🎯 Phase 2 완료 기준

- [x] RP5-B 기본 설정 완료
- [ ] WiFi Direct 연결 성공
- [ ] RP5-A → RP5-B 음성 전송 성공
- [ ] RP5-B → RP5-A 음성 전송 성공
- [ ] Full-Duplex 양방향 통신 성공
- [ ] 레이턴시 < 200ms
- [ ] 1분 이상 안정적 통신

---

## 🚨 예상 문제점 & 해결책

### 1. WiFi Direct 연결 불안정
- **해결**: 채널 고정 (`band bg` 추가)
- **대안**: USB WiFi 동글 사용

### 2. RP5 CPU 부하 (Full-Duplex)
- **확인**: `htop`으로 실시간 모니터링
- **해결**: 버퍼 크기 증가 또는 모델 경량화

### 3. 오디오 디바이스 충돌
- **확인**: `aplay -l`, `arecord -l`
- **해결**: 디바이스 인덱스 명확히 지정

### 4. 모델 파일 전송 실패
- **대안**: GitHub LFS 대신 USB 드라이브 사용

---

## 📌 다음 대화 시작 시 체크사항

1. RP5-B Ubuntu 설치 상태
2. 네트워크 환경 (같은 공간에 있는지)
3. 사용할 오디오 디바이스 (H08A or Bluetooth)
4. 예상 작업 시간
