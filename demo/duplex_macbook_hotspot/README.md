# Full-Duplex Voice Communication (MacBook Hotspot)

실시간 양방향 음성 통신 시스템 - **MacBook Hotspot 네트워크 전용**

## 📌 개요

MacBook의 개인 핫스팟을 통해 두 대의 Raspberry Pi 5를 연결하여 실시간 양방향 음성 통신을 구현합니다.

## 🌐 네트워크 구성

```
MacBook (192.168.2.1)
    ↓ Personal Hotspot
    ├─ RP5-A (192.168.2.2) ←→ UDP 9998/9999 ←→ RP5-B (192.168.2.3)
```

### IP 주소 할당
- **MacBook Hotspot**: `192.168.2.1` (Gateway)
- **RP5-A**: `192.168.2.2` (Client)
- **RP5-B**: `192.168.2.3` (Client)

## ⚙️ 설정 방법

### 1. MacBook Hotspot 설정

**macOS에서:**

1. **시스템 설정** → **일반** → **공유** 열기
2. **인터넷 공유** 활성화:
   - 연결 공유 대상: **Wi-Fi**
   - 다음 포트를 사용하여 컴퓨터 연결: **Wi-Fi**
3. **Wi-Fi 옵션** 클릭:
   - 네트워크 이름: `RP5-Hotspot`
   - 보안: WPA2-Personal
   - 암호: `설정할 암호`
4. **인터넷 공유** 켜기

### 2. RP5-A 네트워크 연결

```bash
# SSH로 RP5-A 접속 후
sudo nmcli device wifi connect "RP5-Hotspot" password "설정한암호"

# IP 확인 (192.168.2.2 할당되었는지 확인)
ip addr show wlan0
```

### 3. RP5-B 네트워크 연결

```bash
# SSH로 RP5-B 접속 후
sudo nmcli device wifi connect "RP5-Hotspot" password "설정한암호"

# IP 확인 (192.168.2.3 할당되었는지 확인)
ip addr show wlan0
```

### 4. 연결 확인

**RP5-A에서:**
```bash
# RP5-B로 ping 테스트
ping 192.168.2.3

# MacBook으로 ping 테스트
ping 192.168.2.1
```

**RP5-B에서:**
```bash
# RP5-A로 ping 테스트
ping 192.168.2.2

# MacBook으로 ping 테스트
ping 192.168.2.1
```

## 🚀 실행 방법

### RP5-A 실행

```bash
cd /home/test1/denoiser/demo/duplex_macbook_hotspot
python start_modular_a.py --config configs/rp5a_macbook.yaml
```

### RP5-B 실행

```bash
cd /home/test1/denoiser/demo/duplex_macbook_hotspot
python start_modular_b.py --config configs/rp5b_macbook.yaml
```

## 📝 설정 파일

### rp5a_macbook.yaml
- **Role**: A (송수신 동시)
- **Peer IP**: `192.168.2.3` (RP5-B)
- **Send Port**: 9999
- **Recv Port**: 9998

### rp5b_macbook.yaml
- **Role**: B (송수신 동시)
- **Peer IP**: `192.168.2.2` (RP5-A)
- **Send Port**: 9998
- **Recv Port**: 9999

## 🔧 문제 해결

### 1. IP 주소가 192.168.2.x 대역이 아닌 경우

MacBook Hotspot의 기본 대역이 다를 수 있습니다.

**해결:**
```bash
# 현재 IP 확인
ip addr show wlan0

# 192.168.2.x가 아니라면 config 파일의 peer_ip를 실제 IP로 수정
# 예: 172.20.10.x 대역인 경우
# rp5a_macbook.yaml: peer_ip를 RP5-B의 실제 IP로
# rp5b_macbook.yaml: peer_ip를 RP5-A의 실제 IP로
```

### 2. Hotspot 연결 불가

```bash
# WiFi 재시작
sudo nmcli radio wifi off
sudo nmcli radio wifi on

# 다시 연결 시도
sudo nmcli device wifi connect "RP5-Hotspot" password "암호"
```

### 3. UDP 통신 실패

```bash
# 방화벽 확인 (RP5)
sudo ufw status
sudo ufw allow 9998/udp
sudo ufw allow 9999/udp

# MacBook 방화벽도 확인 필요 (시스템 설정 → 네트워크 → 방화벽)
```

## ⚠️ 주의사항

1. **MacBook Hotspot은 배터리 소모가 큽니다**
   - 전원 연결 권장

2. **IP 주소 고정 설정 권장**
   - DHCP로 인한 IP 변경 방지
   - NetworkManager 설정으로 고정 IP 할당 가능

3. **통신 범위**
   - 실내: ~10-20m
   - 장애물에 따라 감소

## 📊 성능 예상

- **지연시간**: 100-150ms
- **대역폭**: 양방향 ~40kbps
- **안정성**: WiFi 신호 강도에 따라 변동

## 🔗 관련 문서

- 원본 WiFi Direct 버전: `../duplex/README.md`
- 전체 프로젝트: `/README.md`

---

**작성일**: 2025-11-24
**용도**: MacBook Hotspot 환경 테스트 및 개발
