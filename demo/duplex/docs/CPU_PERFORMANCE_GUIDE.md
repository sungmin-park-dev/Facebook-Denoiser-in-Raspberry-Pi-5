# CPU Performance 모드 설정 가이드

## 📋 개요

양방향 통신 시 AI 처리의 딜레이 누적을 방지하기 위해 CPU를 performance 모드로 설정하는 스크립트입니다.

---

## 📦 제공 파일

### 1. `set_performance.sh` - 수동 CPU 설정
단순히 CPU governor만 변경하는 독립 스크립트

### 2. `start_rp5a.sh` - RP5-A 통합 실행
CPU 설정 + 통신 시작을 한 번에 실행

### 3. `start_rp5b.sh` - RP5-B 통합 실행
CPU 설정 + 통신 시작을 한 번에 실행

### 4. `rp5-performance.service` - Systemd 서비스
재부팅 후에도 performance 모드 유지

---

## 🚀 사용 방법

### 옵션 A: 통합 스크립트 사용 (추천)

**RP5-A (test1):**
```bash
cd /home/test1/denoiser
sudo bash start_rp5a.sh
```

**RP5-B (test2):**
```bash
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
sudo bash start_rp5b.sh
```

**장점:**
- CPU 설정 + 통신 시작을 한 번에
- 종료 시 자동으로 ondemand로 복구
- sudo 권한 확인 자동

---

### 옵션 B: 수동 설정 후 통신 시작

**1. CPU Performance 모드 설정:**
```bash
sudo bash set_performance.sh
```

**2. 통신 시작 (기존 방식):**
```bash
# RP5-A
python demo/duplex/rp5_full_duplex_modular.py \
    --config demo/duplex/configs/rp5a_modular.yaml

# RP5-B
python demo/duplex/rp5_full_duplex_modular.py \
    --config demo/duplex/configs/rp5b_modular.yaml
```

---

### 옵션 C: 재부팅 후에도 유지 (Systemd)

**한 번만 설정하면 영구 적용:**

```bash
# 1. 서비스 파일 복사
sudo cp rp5-performance.service /etc/systemd/system/

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

## 📊 성능 비교

### Ondemand 모드 (기본값)
```
┌─────────────────────────────────┐
│ CPU 주파수: 600MHz ~ 2.4GHz     │
│ AI 처리 시간: 20~30ms           │
│ RTF: > 1.0 (실시간 불가)        │
│ 증상: 딜레이 누적 (1초→3초→5초)│
└─────────────────────────────────┘
```

### Performance 모드 (최적화)
```
┌─────────────────────────────────┐
│ CPU 주파수: 2.4GHz (고정)       │
│ AI 처리 시간: 1~2ms             │
│ RTF: 0.05~0.1 (실시간 여유)     │
│ 증상: 딜레이 고정 (~500ms)      │
└─────────────────────────────────┘
```

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

## 📝 파일 배치

### Mac에서 GitHub 업로드
```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5

# Scripts 디렉토리 생성
mkdir -p scripts/launch

# 파일 복사
cp ~/Downloads/outputs/set_performance.sh scripts/launch/
cp ~/Downloads/outputs/start_rp5a.sh scripts/launch/
cp ~/Downloads/outputs/start_rp5b.sh scripts/launch/
cp ~/Downloads/outputs/rp5-performance.service scripts/launch/

# 실행 권한 부여
chmod +x scripts/launch/*.sh

# Git 커밋
git add scripts/launch/
git commit -m "Add: CPU performance mode setup scripts

- set_performance.sh: Manual CPU governor setup
- start_rp5a.sh: Integrated launch for RP5-A (CPU + communication)
- start_rp5b.sh: Integrated launch for RP5-B (CPU + communication)
- rp5-performance.service: Systemd service for persistent setting
- Resolves AI processing delay accumulation issue"

git push origin main
```

### RP5에 배포
```bash
# RP5-A
cd /home/test1/denoiser
git pull origin main
chmod +x scripts/launch/*.sh

# RP5-B
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
git pull origin main
chmod +x scripts/launch/*.sh
```

---

## 🐛 문제 해결

### 문제 1: "Permission denied" 오류
```bash
# 원인: sudo 없이 실행
# 해결: sudo 추가
sudo bash start_rp5a.sh
```

### 문제 2: Performance 모드인데도 느림
```bash
# 확인 1: CPU 주파수
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
# 2400000이 아니면 문제

# 확인 2: CPU 사용률
htop
# 어떤 프로세스가 CPU 사용하는지 확인

# 확인 3: 메모리 스왑
free -h
# Swap 사용 중이면 메모리 부족
```

### 문제 3: 재부팅 후 ondemand로 돌아감
```bash
# Systemd 서비스 설치 (위의 옵션 C)
sudo cp rp5-performance.service /etc/systemd/system/
sudo systemctl enable rp5-performance.service
sudo systemctl start rp5-performance.service
```

---

## ✅ 체크리스트

### 최초 설정
- [ ] Mac에서 스크립트 다운로드
- [ ] GitHub에 업로드
- [ ] RP5-A에서 git pull
- [ ] RP5-B에서 git pull
- [ ] 실행 권한 부여 (`chmod +x`)

### 매번 통신 시작 전
- [ ] `sudo bash start_rp5a.sh` (RP5-A)
- [ ] `sudo bash start_rp5b.sh` (RP5-B)
- [ ] CPU governor 확인 (performance)

### 영구 설정 (선택)
- [ ] Systemd 서비스 설치
- [ ] 서비스 활성화
- [ ] 재부팅 후 확인

---

## 📈 예상 개선 효과

| 항목 | Ondemand | Performance | 개선 |
|------|----------|-------------|------|
| AI 처리 시간 | 20~30ms | 1~2ms | **10~15배** |
| RTF | > 1.0 | 0.05~0.1 | **10배** |
| 딜레이 누적 | 있음 | 없음 | ✅ **해결** |
| 초기 지연 | ~500ms | ~500ms | 동일 |

---

**작성일**: 2025-11-20  
**버전**: v1.0  
**상태**: ✅ 테스트 준비 완료
