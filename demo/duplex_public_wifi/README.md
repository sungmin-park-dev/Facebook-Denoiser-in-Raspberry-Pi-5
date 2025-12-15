# Full-Duplex Voice Communication (Public WiFi)

실시간 양방향 음성 통신 시스템 - **공용 WiFi 네트워크 전용**

## 📌 개요

공용 WiFi 네트워크(예: Welcome_KAIST)를 통해 두 대의 Raspberry Pi 5를 연결하여 실시간 양방향 음성 통신을 구현합니다.

**주요 특징:**
- 동적 IP 할당 환경에서 자동으로 peer 탐지
- mDNS (hostname.local) 지원
- 서로 다른 서브넷 간 통신 가능 (예: 10.249.55.x ↔ 10.249.98.x)

---

## 🌐 네트워크 구성

```
Public WiFi (Welcome_KAIST)
    ├─ RP5-A (10.249.55.123) ←→ UDP 9998/9999 ←→ RP5-B (10.249.98.234)
    │  (DHCP 동적 할당)                          (DHCP 동적 할당)
    │
    └─ 서브넷이 달라도 작동! (라우팅 지원)
```

### IP 주소 할당
- **RP5-A**: DHCP 자동 할당 (예: 10.249.55.x)
- **RP5-B**: DHCP 자동 할당 (예: 10.249.98.x)
- **동적 IP 문제 해결**: mDNS, 자동 탐지, 수동 입력 지원

---

## 🚀 빠른 시작

### 1. 전제 조건

**양쪽 RP5 모두:**
```bash
# 공용 WiFi에 연결
sudo nmcli device wifi connect "Welcome_KAIST" password "your-password"

# IP 확인
ip addr show wlan0
```

**중요: Client Isolation 확인 필수!**
```bash
# RP5-A에서 RP5-B로 ping 테스트
ping <RP5-B의 IP>

# 만약 ping이 안 되면 해당 WiFi는 Client Isolation이 활성화된 것
# → 다른 WiFi 네트워크를 사용하거나 관리자에게 문의 필요
```

### 2. 실행 방법

**RP5-A:**
```bash
cd ~/denoiser/demo/duplex_public_wifi
python start_modular_a.py
```

**RP5-B:**
```bash
cd ~/Facebook-Denoiser-in-Raspberry-Pi-5/demo/duplex_public_wifi
python start_modular_b.py
```

스크립트가 자동으로:
1. Public WiFi 연결 확인
2. Peer IP 해석 (mDNS → 자동 탐지 → 수동 입력)
3. 오디오 장치 선택
4. 통신 시작

---

## ⚙️ IP 동적 할당 문제 해결

공용 WiFi는 DHCP로 IP를 할당하므로 재연결할 때마다 IP가 변경될 수 있습니다.

### 해결 방법 (우선순위 순)

#### 1. mDNS Hostname (권장) ✅

**설정:**
```yaml
# configs/rp5a_public.yaml
peer_ip: "test2-desktop.local"  # RP5-B의 호스트명

# configs/rp5b_public.yaml
peer_ip: "test1-desktop.local"  # RP5-A의 호스트명
```

**장점:**
- IP 변경 시에도 자동 해석
- 설정 후 변경 불필요

**확인 방법:**
```bash
# 호스트명 확인
hostname

# mDNS 해석 테스트
ping test2-desktop.local
```

#### 2. 명령행 옵션

실행 시 peer IP를 직접 지정:
```bash
python start_modular_a.py --peer-ip 10.249.98.234
```

#### 3. 자동 탐지

스크립트가 자동으로 같은 서브넷을 스캔하여 peer를 찾습니다.
- Ping sweep 방식
- 발견된 IP를 사용자에게 확인 요청

#### 4. 수동 입력

위 방법들이 모두 실패하면 대화형 입력으로 IP 주소를 직접 입력합니다.

---

## 📝 설정 파일

### configs/rp5a_public.yaml
```yaml
role: A
peer_ip: "test2-desktop.local"  # mDNS hostname 또는 IP
mic_device: 1
speaker_device: 1
send_port: 9999
recv_port: 9998
model: Light-32-Depth4
```

### configs/rp5b_public.yaml
```yaml
role: B
peer_ip: "test1-desktop.local"  # mDNS hostname 또는 IP
mic_device: 1
speaker_device: 1
send_port: 9998
recv_port: 9999
model: Light-32-Depth4
```

**peer_ip 옵션:**
- `"hostname.local"` - mDNS 자동 해석 (권장)
- `"10.249.98.123"` - 고정 IP (알고 있는 경우)
- `null` - 실행 시 자동 탐지 또는 수동 입력

---

## 🔧 문제 해결

### 1. Client Isolation 활성화된 경우

**증상:**
```bash
ping <peer-ip>
# → 100% packet loss
```

**해결:**
- WiFi 관리자에게 문의하여 Client Isolation 비활성화 요청
- 또는 다른 WiFi 네트워크 사용 (예: 개인 라우터)
- WiFi Direct 방식 사용: `../duplex/` 디렉토리 참조

### 2. mDNS 해석 실패

**증상:**
```
❌ Failed to resolve test2-desktop.local
```

**해결:**
```bash
# Avahi 서비스 확인 (mDNS 데몬)
sudo systemctl status avahi-daemon

# 재시작
sudo systemctl restart avahi-daemon

# 호스트명 확인
hostname
# → RP5-A는 "test1-desktop", RP5-B는 "test2-desktop"으로 설정되어야 함
```

### 3. 서브넷이 다른 경우 통신 안 됨

**증상:**
- RP5-A: 10.249.55.x
- RP5-B: 10.249.98.x
- ping 성공하지만 UDP 통신 실패

**해결:**
```bash
# 라우팅 테이블 확인
ip route

# 방화벽 확인 (RP5)
sudo ufw status
sudo ufw allow 9998/udp
sudo ufw allow 9999/udp
```

**확인된 작동 환경:**
- MacBook (10.249.55.123) ↔ RP5-B (10.249.98.234): ✅ 정상 작동
- 패킷 손실: 0%
- 평균 지연: 35-40ms

### 4. WiFi 연결 불안정

```bash
# WiFi 재연결
sudo nmcli device disconnect wlan0
sudo nmcli device wifi connect "Welcome_KAIST" password "password"

# 연결 상태 확인
nmcli connection show --active
```

### 5. IP 자동 탐지가 너무 느림

**해결:**
- 명령행 옵션 사용: `--peer-ip 10.249.98.234`
- 또는 config에 고정 IP 설정 (임시)

---

## ⚠️ 주의사항

### 1. Client Isolation 필수 확인
공용 WiFi의 대부분은 보안상 Client Isolation이 활성화되어 있습니다.
- 실행 전 반드시 `ping <peer-ip>`로 확인 필요
- Client Isolation이 켜져 있으면 절대 통신 불가

### 2. 방화벽 설정
```bash
# UDP 포트 9998, 9999 열기
sudo ufw allow 9998/udp
sudo ufw allow 9999/udp
```

### 3. IP 변경 빈도
- 공용 WiFi는 재연결 시 IP가 변경될 수 있음
- **mDNS 사용 권장** (hostname.local)
- 또는 매번 `--peer-ip` 옵션으로 실행

### 4. 네트워크 안정성
- 공용 WiFi는 혼잡도에 따라 성능 변동 가능
- 안정적인 통신을 위해 혼잡하지 않은 시간대 사용 권장

---

## 📊 성능 (테스트 완료)

**테스트 환경:**
- WiFi: Welcome_KAIST
- MacBook (10.249.55.123) ↔ RP5-B (10.249.98.234)
- 서브넷: 다름 (55 vs 98)

**결과:**
- **지연시간**: 평균 35-40ms
- **패킷 손실**: 0%
- **안정성**: 양방향 통신 성공 ✅

---

## 🆚 다른 버전과 비교

| 특징 | duplex (WiFi Direct) | duplex_public_wifi (Public WiFi) |
|------|----------------------|--------------------------------------|
| 네트워크 | WiFi Direct (10.42.0.x) | 공용 WiFi (DHCP) |
| IP 할당 | 고정 IP | 동적 IP (mDNS 지원) |
| 설정 난이도 | 중간 (AP 설정 필요) | 쉬움 (WiFi만 연결) |
| 안정성 | 높음 | WiFi 품질에 따라 변동 |
| 서브넷 간 통신 | N/A (같은 네트워크) | 가능 (라우팅 지원) |
| Client Isolation | 없음 | 확인 필수 |
| 권장 사용 | 운영/실제 사용 | 테스트/개발 |

---

## 🔗 관련 문서

- **WiFi Direct 버전 (안정적)**: `../duplex/README.md`
- **전체 프로젝트**: `/README.md`
- **아키텍처**: `/docs/ARCHITECTURE.md`
- **설치 가이드**: `/docs/SETUP_GUIDE.md`

---

## 📚 추가 정보

### 스크립트 사용법

**기본 실행:**
```bash
python start_modular_a.py
```

**Peer IP 지정:**
```bash
python start_modular_a.py --peer-ip 10.249.98.234
```

**커스텀 Config 사용:**
```bash
python start_modular_a.py --config configs/custom.yaml
```

### mDNS 설정 (선택사항)

호스트명 변경:
```bash
# RP5-A
sudo hostnamectl set-hostname test1-desktop

# RP5-B
sudo hostnamectl set-hostname test2-desktop

# 재부팅 또는 Avahi 재시작
sudo systemctl restart avahi-daemon
```

---

**작성일**: 2025-12-06
**버전**: v2.0 (Public WiFi)
**용도**: 공용 WiFi 환경에서 테스트 및 개발
**상태**: 테스트 완료 ✅
