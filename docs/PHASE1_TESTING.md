# Phase 1: Mac ↔ RP5-A Testing Guide

## 🎯 목표
Mac에서 RP5-A로 음성 전송 및 수신 테스트

---

## 📋 사전 준비

### 1. 네트워크 설정
**Mac과 RP5-A를 동일한 WiFi에 연결**
```bash
# Mac IP 확인
ifconfig en0 | grep "inet "
# 예: inet 10.249.55.35

# RP5-A IP 확인
ip addr show wlan0 | grep "inet "
# 예: inet 10.249.55.101

# 연결 테스트
# Mac에서
ping [RP5-A IP]

# RP5-A에서
ping 10.249.55.35
```

### 2. 의존성 설치

**Mac:**
```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5
conda activate denoiser_modern

# opuslib 설치
brew install opus  # 이미 설치됨
pip install opuslib  # 이미 설치됨
```

**RP5-A:**
```bash
cd /home/test1/denoiser
source /home/test1/venv/bin/activate

# opuslib 설치
sudo apt-get update
sudo apt-get install libopus0 libopus-dev
pip install opuslib
```

### 3. 프로젝트 코드 동기화

**RP5-A에서:**
```bash
cd /home/test1/denoiser

# GitHub에서 최신 코드 pull
git pull origin main
```

---

## 🧪 Test 1: Mac → RP5-A (단방향 송신)

### RP5-A (수신기 먼저 실행)
```bash
cd /home/test1/denoiser
source /home/test1/venv/bin/activate

# 오디오 디바이스 확인
python scripts/rp5_receiver.py --list-devices

# 수신 시작 (Device 1 = H08A)
python scripts/rp5_receiver.py --port 5000 --device 1
```

**예상 출력:**
```
✅ RP5AudioReceiver initialized:
   Listening on port: 5000
   Speaker device: 1
   Buffer size: 10 frames
👂 Listening on port 5000...
Press Ctrl+C to stop...
```

### Mac (송신기 실행)
```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5
conda activate denoiser_modern

# 마이크 디바이스 확인
python scripts/mac_sender.py --list-devices

# 송신 시작 (RP5 IP 입력)
python scripts/mac_sender.py --rp5-ip [RP5-A IP] --port 5000
```

**예상 출력:**
```
✅ OpusCodec initialized:
   Sample rate: 16000 Hz
   Channels: 1
   Bitrate: 16000 bps
   Frame size: 320 samples (20ms)
🤖 Loading Light-32-Depth4...
✅ MacAudioSender initialized:
   Target: [RP5-A IP]:5000
   Mic device: default
   Model: Light-32-Depth4
🎙️ Starting audio capture...
📡 Sending to [RP5-A IP]:5000
Press Ctrl+C to stop...

📊 Sent 250 packets in 5.0s
```

### 검증
1. Mac 마이크에 말하기
2. RP5-A 스피커에서 음성 들림 (약 50-100ms 지연)
3. 5초마다 통계 확인

---

## 🐛 문제 해결 (Troubleshooting)

### 1. "Connection refused" 오류
```bash
# 방화벽 확인 (Mac)
sudo pfctl -s rules | grep 5000

# 방화벽 비활성화 (테스트용)
sudo pfctl -d
```

### 2. "No audio output" (RP5-A)
```bash
# ALSA 디바이스 확인
aplay -l

# H08A 디바이스 테스트
speaker-test -D hw:1,0 -c 2 -r 48000
```

### 3. "Module not found: opuslib"
```bash
# Mac (Homebrew)
brew install opus
pip install opuslib

# RP5-A (APT)
sudo apt-get install libopus0 libopus-dev
pip install opuslib
```

### 4. "Buffer underrun" 경고
```bash
# 버퍼 크기 증가
python scripts/rp5_receiver.py --buffer 20
```

### 5. 음질이 나쁨
- 네트워크 지연 확인: `ping [RP5-A IP]`
- CPU 부하 확인: `htop` (RP5-A)
- WiFi 신호 강도 확인

---

## 📊 성능 측정

### 레이턴시 측정
```bash
# Mac에서 테스트 톤 재생
# RP5-A에서 녹음
# Audacity로 시간차 분석
```

### 패킷 통계
- 5초마다 자동 출력
- 목표: 50 packets/s (20ms/packet)
- 손실률: < 1%

---

## ✅ 성공 기준

1. **연결 성공**: 첫 패킷 수신 메시지 출력
2. **음성 전달**: Mac 말 → RP5-A 스피커 출력
3. **지연 시간**: < 100ms
4. **패킷 손실**: < 1%
5. **안정성**: 1분 이상 끊김 없음

---

## 🚀 다음 단계

Test 1 성공 후:
1. Mac 수신기 구현
2. Full-Duplex (양방향) 통합
3. 레이턴시 최적화
4. Phase 2로 이동 (RP5-A ↔ RP5-B)