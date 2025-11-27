# RP5 설치 및 설정 가이드

## 📋 개요

Raspberry Pi 5에서 실시간 음성 디노이징 시스템을 설치하고 설정하는 전체 가이드입니다.

---

## ⚙️ 환경 설정 (RP5)

### 1. 시스템 요구사항

- **하드웨어**: Raspberry Pi 5 (8GB RAM 권장)
- **OS**: Ubuntu 24.04 LTS
- **Python**: 3.9+
- **오디오**: USB Audio Interface (H08A 등)

### 2. 가상환경 생성

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

### 3. 프로젝트 클론

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/Facebook-Denoiser-in-Raspberry-Pi-5.git
cd Facebook-Denoiser-in-Raspberry-Pi-5
```

---

## 🎵 오디오 디바이스 설정

### 1. 디바이스 확인

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### 2. H08A USB Audio 설정

```
Device: H08A Audio USB (hw:1,0)
- Input Channels: 2 (Stereo)
- Output Channels: 2 (Stereo)
- Sample Rate: 48kHz
```

### 3. ALSA 설정

```bash
# /etc/asound.conf 또는 ~/.asoundrc 편집
sudo nano /etc/asound.conf
```

```
pcm.!default {
    type hw
    card 1
    device 0
}
```

---

## 🚀 CPU Performance 모드 설정

### 왜 필요한가?

양방향 통신 시 AI 처리의 딜레이 누적을 방지하기 위해 CPU를 performance 모드로 설정합니다.

### 성능 비교

| 모드 | CPU 주파수 | AI 처리 시간 | RTF | 딜레이 누적 |
|------|-----------|-------------|-----|----------|
| **Ondemand** (기본) | 600MHz~2.4GHz | 20~30ms | >1.0 | ❌ 있음 (1초→3초→5초) |
| **Performance** | 2.4GHz 고정 | 1~2ms | 0.05~0.1 | ✅ 없음 (~500ms 고정) |

### 옵션 A: 통합 스크립트 사용 (추천)

**RP5-A (test1):**
```bash
cd /home/test1/denoiser
sudo bash demo/duplex/start_rp5a.sh
```

**RP5-B (test2):**
```bash
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
sudo bash demo/duplex/start_rp5b.sh
```

**장점:**
- CPU 설정 + 통신 시작을 한 번에
- 종료 시 자동으로 ondemand로 복구
- sudo 권한 확인 자동

### 옵션 B: 수동 설정

**1. CPU Performance 모드 설정:**
```bash
sudo bash demo/duplex/set_performance.sh
```

**2. 통신 시작:**
```bash
# RP5-A
python demo/duplex/start_modular_a.py --config demo/duplex/configs/rp5a_modular.yaml

# RP5-B
python demo/duplex/start_modular_b.py --config demo/duplex/configs/rp5b_modular.yaml
```

### 옵션 C: 재부팅 후에도 유지 (Systemd)

**한 번만 설정하면 영구 적용:**

```bash
# 1. 서비스 파일 복사
sudo cp demo/duplex/rp5-performance.service /etc/systemd/system/

# 2. 서비스 활성화
sudo systemctl enable rp5-performance.service

# 3. 즉시 시작
sudo systemctl start rp5-performance.service

# 4. 확인
systemctl status rp5-performance.service
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

**이후 재부팅해도 자동으로 performance 모드 유지!**

---

## 🔍 확인 방법

### CPU Governor 확인

```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
# 출력: performance (OK) 또는 ondemand (변경 필요)
```

### CPU 주파수 실시간 모니터링

```bash
# 새 터미널에서 실행
watch -n 0.5 "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"

# Performance: 2400000 (고정)
# Ondemand: 600000~2400000 (변동)
```

---

## 🌐 WiFi 네트워크 설정

### WiFi Direct (demo/duplex/)

**RP5-A (Access Point):**
```bash
sudo nmcli device wifi hotspot ssid "RP5-Direct" password "secure123"
```

**RP5-B (Client):**
```bash
sudo nmcli device wifi connect "RP5-Direct" password "secure123"
```

**IP 확인:**
```bash
ip addr show wlan0
# RP5-A: 10.42.0.1
# RP5-B: 10.42.0.x
```

### MacBook Hotspot (demo/duplex_macbook_hotspot/)

자세한 내용은 `demo/duplex_macbook_hotspot/README.md` 참조

---

## 🐛 문제 해결

### 1. Permission denied 오류

```bash
# 원인: sudo 없이 실행
# 해결: sudo 추가
sudo bash demo/duplex/start_rp5a.sh
```

### 2. Performance 모드인데도 느림

```bash
# 확인 1: CPU 주파수
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
# 2400000이 아니면 문제

# 확인 2: CPU 사용률
htop

# 확인 3: 메모리 스왑
free -h
# Swap 사용 중이면 메모리 부족
```

### 3. 재부팅 후 ondemand로 돌아감

```bash
# Systemd 서비스 설치 (위의 옵션 C)
sudo cp demo/duplex/rp5-performance.service /etc/systemd/system/
sudo systemctl enable rp5-performance.service
sudo systemctl start rp5-performance.service
```

### 4. Input Overflow 경고

```
⚠️ Input: input overflow

원인: 처리 속도가 입력 속도보다 느림 (RTF > 1.0)
해결: Performance 모드 설정 또는 더 가벼운 모델 사용
```

### 5. 모델 로딩 실패

```bash
# torch.hub 캐시 초기화
rm -rf ~/.cache/torch/hub
```

### 6. ALSA 채널 오류

```
Error: Invalid number of channels [PaErrorCode -9998]

해결: H08A는 스테레오(2채널) → channels=2 설정
```

---

## 📊 모델별 설정

### Light-32-Depth4 (권장)

```bash
# RP5에서 실시간 처리 가능
python demo/duplex/start_modular_a.py --config demo/duplex/configs/rp5a_modular.yaml
```

**성능:**
- RTF: 0.071 (실시간의 14배 여유)
- 파라미터: 434K
- 크기: 1.67MB

### dns48/dns64 (원본 모델)

```bash
# 테스트용 (실시간 불가)
# 코드 내 MODEL_NAME 변경 필요
```

**성능:**
- dns48: RTF 1.484 (❌ Overflow 발생)
- dns64: RTF 1.887 (❌ Overflow 발생)

---

## ✅ 체크리스트

### 최초 설정
- [ ] Python 가상환경 생성
- [ ] 의존성 패키지 설치
- [ ] 프로젝트 클론
- [ ] 오디오 디바이스 확인
- [ ] CPU Performance 모드 설정

### WiFi 통신 설정
- [ ] WiFi Direct 또는 Hotspot 연결
- [ ] IP 주소 확인
- [ ] ping 테스트 성공

### 매번 통신 시작 전
- [ ] `sudo bash start_rp5a.sh` (RP5-A)
- [ ] `sudo bash start_rp5b.sh` (RP5-B)
- [ ] CPU governor 확인 (performance)

---

## 🔗 관련 문서

- 아키텍처 설명: `ARCHITECTURE.md`
- Phase 완료 기록: `COMPLETED_PHASES.md`
- 프로젝트 개요: `/README.md`
- MacBook Hotspot: `demo/duplex_macbook_hotspot/README.md`

---

**작성일**: 2025-11-26
**버전**: v1.0
**통합 문서**: CPU_PERFORMANCE_GUIDE.md + 환경 설정 가이드
