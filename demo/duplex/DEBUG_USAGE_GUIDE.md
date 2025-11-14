# RP5 Full-Duplex DEBUG 사용 가이드

## 🎯 목적

WiFi 양방향 통신 검증 전용 (AI 기능 제외)

**이 버전의 특징:**
- ✅ AI 디노이징 완전 제거 (direct passthrough)
- ✅ 최대 디버그 출력
- ✅ 데이터 타입 추적
- ✅ 각 단계별 레벨 모니터링
- ✅ 기존 코드 손상 없음

---

## 📁 파일 구조

```
demo/duplex/
├── rp5_full_duplex_debug.py      # 메인 스크립트 (AI 제거)
├── start_debug_a.py               # RP5-A 실행 스크립트
├── start_debug_b.py               # RP5-B 실행 스크립트
└── configs/
    ├── rp5a_debug.yaml            # A 설정
    └── rp5b_debug.yaml            # B 설정
```

---

## 📋 설치 방법

### Mac에서

```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5

# 파일 복사
cp /path/to/rp5_full_duplex_debug.py demo/duplex/
cp /path/to/start_debug_a.py demo/duplex/
cp /path/to/start_debug_b.py demo/duplex/
cp /path/to/rp5a_debug.yaml demo/duplex/configs/
cp /path/to/rp5b_debug.yaml demo/duplex/configs/

# 실행 권한 부여
chmod +x demo/duplex/start_debug_a.py
chmod +x demo/duplex/start_debug_b.py

# Git 커밋
git add demo/duplex/rp5_full_duplex_debug.py
git add demo/duplex/start_debug_a.py
git add demo/duplex/start_debug_b.py
git add demo/duplex/configs/rp5a_debug.yaml
git add demo/duplex/configs/rp5b_debug.yaml

git commit -m "Add: Full-duplex DEBUG version for WiFi communication testing"
git push origin main
```

### RP5-A & RP5-B에서

```bash
# RP5-A
cd /home/test1/denoiser
git pull origin main

# RP5-B
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
git pull origin main
```

---

## 🚀 실행 방법

### Step 1: WiFi Direct 연결 확인

**RP5-A (AP):**
```bash
nmcli device status | grep p2p
# 예상: p2p-dev-wlan0  wifi  connected  RP5-Direct
```

**RP5-B (Client):**
```bash
nmcli connection show | grep RP5-Direct
# 예상: RP5-Direct  xxx-xxx-xxx  wifi  --
```

**네트워크 확인:**
```bash
# RP5-A
ping 10.42.0.224  # RP5-B

# RP5-B
ping 10.42.0.1    # RP5-A
```

---

### Step 2: 실행 (대화형)

**RP5-A:**
```bash
cd /home/test1/denoiser
source venv/bin/activate

python demo/duplex/start_debug_a.py
# 디바이스 선택 후 시작
```

**RP5-B:**
```bash
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
source venv_denoiser/bin/activate

python demo/duplex/start_debug_b.py
# 디바이스 선택 후 시작
```

---

## 🔍 예상 출력

### ✅ 정상 작동 시

**RP5-A (송신측):**
```
[TX DEBUG #50]
  🎤 Mic level: 0.4523
  📊 audio_16k_flat:
     dtype: float32
     shape: (320,)
     range: [-0.4523, 0.4891]
     mean: 0.0012
     abs_max: 0.4891
  📦 Encoded packet:
     size: 41 bytes
     first 10 bytes: 1a2f3b4c5d6e7f8091a2

📊 TX: 50 (50.0 pkt/s) | RX: 50 (50.0 pkt/s) | 🎤 0.450 | 📦 0.489 | 📥 0.000 | 🔊 0.000 | ⏱️ 1s
```

**RP5-B (수신측):**
```
[RX DEBUG #50]
  📡 Received packet:
     size: 41 bytes
     from: ('10.42.0.1', 54321)
     first 10 bytes: 1a2f3b4c5d6e7f8091a2
  🔓 Decoded audio:
     dtype: float32
     shape: (320,)
     range: [-0.4519, 0.4889]
     abs_max: 0.4889
  ⬆️ Upsampled audio:
     abs_max: 0.4890
     samples: 320 → 960
  🔊 Speaker level: 0.488

📊 TX: 50 (50.0 pkt/s) | RX: 50 (50.0 pkt/s) | 🎤 0.450 | 📦 0.489 | 📥 0.489 | 🔊 0.488 | ⏱️ 1s
```

**✅ 성공 지표:**
1. TX/RX 패킷 수 일치
2. 패킷 크기 40-50 bytes
3. decoded abs_max > 0.1 (큰 소리일 때)
4. 🔊 Speaker level > 0 (실제 소리 출력)

---

### ❌ 문제 발생 시

**케이스 1: 빈 패킷**
```
[TX DEBUG #50]
  📦 Encoded packet:
     size: 0 bytes  ← 문제!
     ❌ WARNING: Empty packet!
```
→ **원인**: Opus 인코딩 실패 (데이터 타입 문제)

**케이스 2: 수신 데이터 = 0**
```
[RX DEBUG #50]
  🔓 Decoded audio:
     abs_max: 0.0002  ← 거의 0!
  🔊 Speaker level: 0.000
```
→ **원인**: 패킷 손실 또는 디코딩 실패

**케이스 3: 네트워크 문제**
```
📊 TX: 100 (50.0 pkt/s) | RX: 0 (0.0 pkt/s)  ← RX = 0!
```
→ **원인**: WiFi Direct 연결 문제 또는 포트 문제

---

## 🐛 문제 해결

### 1. 소리가 안 들림

**진단:**
```bash
# RP5-B에서 디버그 출력 확인
# 만약 decoded abs_max = 0 이면 네트워크 문제
# 만약 decoded abs_max > 0 인데 소리 없으면 스피커 문제
```

**해결:**
```bash
# 스피커 테스트
speaker-test -D hw:1,0 -c 2

# 다른 디바이스 시도
python demo/duplex/start_debug_b.py
# 디바이스 번호 변경
```

---

### 2. 패킷 크기 = 0

**진단:**
```bash
# TX DEBUG에서 audio_16k_flat 확인
# 만약 abs_max = 0 이면 마이크 문제
# 만약 abs_max > 0 인데 packet size = 0 이면 Opus 문제
```

**해결:**
```bash
# 마이크 테스트
arecord -D hw:1,0 -f S16_LE -r 16000 -d 5 test.wav

# Opus 재설치
pip install --force-reinstall opuslib
```

---

### 3. RX = 0 (패킷 수신 안됨)

**진단:**
```bash
# 네트워크 연결 확인
ping [peer_ip]

# 포트 확인
sudo netstat -tulpn | grep 9998
sudo netstat -tulpn | grep 9999
```

**해결:**
```bash
# WiFi Direct 재연결
nmcli connection down RP5-Direct
nmcli connection up RP5-Direct

# 방화벽 비활성화 (테스트용)
sudo ufw disable
```

---

## 📊 성공 기준

### ✅ WiFi 통신 검증 완료 조건

1. **패킷 전송**: TX > 0, RX > 0
2. **패킷 크기**: 40-50 bytes (일관성)
3. **데이터 레벨**: 
   - 🎤 Mic level > 0.1 (말할 때)
   - 📦 Encoded level ≈ Mic level
   - 📥 Decoded level ≈ Encoded level
   - 🔊 Speaker level ≈ Decoded level
4. **소리 출력**: 실제로 스피커에서 들림

### ✅ 통신 성공 시 다음 단계

1. 기존 `rp5_full_duplex.py` 수정
2. AI toggle 기능 복원
3. AI 디노이징 테스트

---

## 📝 참고사항

### 디버그 출력 빈도

- 50번마다 상세 출력
- 1초마다 stats 업데이트
- 너무 많은 출력 시 성능 저하 가능

### 데이터 흐름

```
송신: Mic(48k) → Downsample(16k) → Encode → UDP
수신: UDP → Decode(16k) → Upsample(48k) → Speaker
```

### 주요 차이점

| 항목 | 기존 버전 | DEBUG 버전 |
|------|----------|-----------|
| AI 디노이징 | O (toggle) | X (제거) |
| 디버그 출력 | 최소 | 최대 |
| 코드 복잡도 | 높음 | 낮음 |
| 목적 | 실사용 | 통신 검증 |

---

## 🎯 최종 목표

**이 DEBUG 버전으로 WiFi 통신이 확인되면:**

1. 데이터 타입 문제 해결 확인
2. 네트워크 설정 검증
3. Opus 코덱 동작 확인

**그 후:**

1. 기존 `rp5_full_duplex.py`에 수정 적용
2. AI toggle 기능 복원
3. Task A (필터 체인) 작업 진행

---

**작성**: 2025-11-14 | **버전**: v1.0 (DEBUG)
