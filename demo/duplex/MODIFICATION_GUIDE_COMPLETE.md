# 🔧 RP5 Full-Duplex 수정 가이드

## 📋 수정 파일 요약

### 1️⃣ rp5_full_duplex.py (포트 스왑 제거)
**문제**: Role B의 포트 스왑 로직이 이중 스왑을 일으켜 패킷 수신 실패
**해결**: 포트 스왑 로직 제거

### 2️⃣ start_full_duplex_a.py / start_full_duplex_b.py (파일 분리)
**문제**: 하나의 파일에서 ROLE 변수 수정 필요, VSCode에서 직접 실행 불편
**해결**: A, B용 파일 분리, 함수는 동일하고 실행부에서만 변수 설정

---

## 🖥️ Mac에서 수정 작업

### Step 1: Mac 로컬 저장소 이동
```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5
```

### Step 2: 수정된 파일 복사
```bash
# 1. rp5_full_duplex.py 백업
cp demo/duplex/rp5_full_duplex.py demo/duplex/rp5_full_duplex.py.backup

# 2. 수정된 파일 복사 (첨부된 파일에서)
# - rp5_full_duplex_fixed.py → demo/duplex/rp5_full_duplex.py
# - start_full_duplex_a.py → demo/duplex/start_full_duplex_a.py  
# - start_full_duplex_b.py → demo/duplex/start_full_duplex_b.py
```

### Step 3: Git 커밋 및 푸시
```bash
# 변경사항 확인
git status

# 변경된 파일 추가
git add demo/duplex/rp5_full_duplex.py
git add demo/duplex/start_full_duplex_a.py
git add demo/duplex/start_full_duplex_b.py

# 커밋
git commit -m "Fix: Port swap issue and split start scripts for A/B

- Remove port swap logic in FullDuplexComm (caused double swapping)
- Split start_full_duplex.py into A/B specific files
- Functions remain identical, only config differs in __main__"

# GitHub에 푸시
git push origin main
```

---

## 🔧 RP5-A (test1) 업데이트

```bash
# SSH 접속
ssh test1@10.42.0.1

# 프로젝트 디렉토리 이동
cd ~/denoiser

# Git pull
git pull origin main

# 변경사항 확인
git log -1 --stat

# 파일 확인
ls -l demo/duplex/start_full_duplex_a.py
ls -l demo/duplex/rp5_full_duplex.py
```

---

## 🔧 RP5-B (test2) 업데이트

```bash
# SSH 접속  
ssh test2@10.42.0.224

# 프로젝트 디렉토리 이동
cd ~/Facebook-Denoiser-in-Raspberry-Pi-5

# Git pull
git pull origin main

# 변경사항 확인
git log -1 --stat

# 파일 확인
ls -l demo/duplex/start_full_duplex_b.py
ls -l demo/duplex/rp5_full_duplex.py
```

---

## 🧪 테스트

### RP5-A에서:
```bash
cd ~/denoiser
source venv/bin/activate

# Option 1: 직접 실행 스크립트 (추천)
python demo/duplex/start_full_duplex_a.py

# Option 2: config 파일로 실행
python demo/duplex/rp5_full_duplex.py --config demo/duplex/configs/rp5a_config.yaml
```

### RP5-B에서:
```bash
cd ~/Facebook-Denoiser-in-Raspberry-Pi-5
source venv_denoiser/bin/activate

# Option 1: 직접 실행 스크립트 (추천)
python demo/duplex/start_full_duplex_b.py

# Option 2: config 파일로 실행
python demo/duplex/rp5_full_duplex.py --config demo/duplex/configs/rp5b_config.yaml
```

---

## ✅ 성공 기준

### RP5-A 출력:
```
✅ FullDuplexComm initialized (Role A):
   Peer: 10.42.0.224
   Sending: 10.42.0.224:9999   ✅
   Receiving: 0.0.0.0:9998     ✅

📊 Sent: 250, Recv: 245 (5.0s)
   Send rate: 50.0 packets/s
   Recv rate: 49.0 packets/s   ✅
```

### RP5-B 출력:
```
✅ FullDuplexComm initialized (Role B):
   Peer: 10.42.0.1
   Sending: 10.42.0.1:9998     ✅ (이전: 9999)
   Receiving: 0.0.0.0:9999     ✅ (이전: 9998)

📊 Sent: 250, Recv: 248 (5.0s)
   Send rate: 50.0 packets/s
   Recv rate: 49.6 packets/s   ✅ (이전: 0.0)
```

### 확인사항:
- ✅ Recv rate가 0이 아닌 ~50 packets/s
- ✅ "📥 Decoded level: X.XXXX" 메시지 출력
- ✅ "🔊 Speaker level: X.XXXX" 메시지 출력
- ✅ 실제로 양쪽에서 소리가 들림!

---

## 🎯 주요 변경사항 상세

### 1. rp5_full_duplex.py (Line 54-60)

**Before:**
```python
# Port assignment (A and B use opposite ports)
if role == 'A':
    self.send_port = send_port
    self.recv_port = recv_port
else:  # role == 'B'
    self.send_port = recv_port  # ❌ 스왑 - 이중 스왑 발생!
    self.recv_port = send_port  # ❌ 스왑 - 이중 스왑 발생!
```

**After:**
```python
# Port assignment (use as configured in YAML)
# ✅ FIXED: Removed port swap logic for Role B
self.send_port = send_port
self.recv_port = recv_port
```

### 2. start_full_duplex_a.py

**구조:**
```python
# 함수들 (동일)
def run_cmd(...): ...
def check_wifi_direct(...): ...
def check_git(...): ...
def activate_venv(...): ...
def run_full_duplex(...): ...
def main(role, config): ...

# RP5-A 전용 설정 (여기만 다름!)
if __name__ == "__main__":
    ROLE = "A"
    CONFIG = {
        "role": "A",
        "project_dir": "~/denoiser",
        "venv": "venv",
        "peer_ip": "10.42.0.224",
        "my_ip": "10.42.0.1",
        "send_port": 9999,
        "recv_port": 9998,
        ...
    }
    main(ROLE, CONFIG)
```

### 3. start_full_duplex_b.py

**구조:**
```python
# 함수들 (A와 완전 동일)
def run_cmd(...): ...
def check_wifi_direct(...): ...
def check_git(...): ...
def activate_venv(...): ...
def run_full_duplex(...): ...
def main(role, config): ...

# RP5-B 전용 설정 (여기만 다름!)
if __name__ == "__main__":
    ROLE = "B"
    CONFIG = {
        "role": "B",
        "project_dir": "~/Facebook-Denoiser-in-Raspberry-Pi-5",
        "venv": "venv_denoiser",
        "peer_ip": "10.42.0.1",
        "my_ip": "10.42.0.224",
        "send_port": 9998,
        "recv_port": 9999,
        ...
    }
    main(ROLE, CONFIG)
```

---

## 🎉 VSCode에서 직접 실행

### RP5-A에서:
1. VSCode로 `demo/duplex/start_full_duplex_a.py` 열기
2. ▶ Run 버튼 클릭
3. 자동으로 WiFi 체크, Git 확인, venv 활성화, full-duplex 시작!

### RP5-B에서:
1. VSCode로 `demo/duplex/start_full_duplex_b.py` 열기
2. ▶ Run 버튼 클릭
3. 자동으로 WiFi 체크, Git 확인, venv 활성화, full-duplex 시작!

---

## 📝 문제 해결 (Troubleshooting)

### 여전히 Recv: 0인 경우
```bash
# 1. 포트가 올바르게 설정되었는지 확인
# RP5-B에서 실행 시 로그 확인:
✅ FullDuplexComm initialized (Role B):
   Sending: 10.42.0.1:9998     # 이게 9999면 아직 안 고쳐진 것
   Receiving: 0.0.0.0:9999     # 이게 9998이면 아직 안 고쳐진 것

# 2. 파일이 제대로 업데이트 되었는지 확인
grep -A 5 "Port assignment" demo/duplex/rp5_full_duplex.py

# 올바른 출력:
# Port assignment (use as configured in YAML)
# ✅ FIXED: Removed port swap logic for Role B
self.send_port = send_port
self.recv_port = recv_port
```

### 방화벽 문제
```bash
# UDP 포트 9998, 9999 확인
sudo ufw status
sudo ufw allow 9998/udp
sudo ufw allow 9999/udp
```

---

**최종 업데이트**: 2025-11-03
**버전**: 2.0
**상태**: Ready to deploy
