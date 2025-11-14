# RP5 Full-Duplex DEBUG - 빠른 시작

## 🚀 5분 안에 테스트하기

### Mac에서 (1분)

```bash
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5

# Outputs 디렉토리에서 파일 복사
cp /path/to/outputs/rp5_full_duplex_debug.py demo/duplex/
cp /path/to/outputs/start_debug_a.py demo/duplex/
cp /path/to/outputs/start_debug_b.py demo/duplex/
cp /path/to/outputs/rp5a_debug.yaml demo/duplex/configs/
cp /path/to/outputs/rp5b_debug.yaml demo/duplex/configs/

chmod +x demo/duplex/start_debug_*.py

git add demo/duplex/*debug* demo/duplex/configs/*debug*
git commit -m "Add: Full-duplex DEBUG for WiFi testing (NO AI)"
git push origin main
```

---

### RP5-A & RP5-B에서 (각 1분)

```bash
# RP5-A
cd /home/test1/denoiser
git pull origin main

# RP5-B  
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
git pull origin main
```

---

### 실행 (각 1분)

**RP5-A:**
```bash
cd /home/test1/denoiser
source venv/bin/activate
python demo/duplex/start_debug_a.py
```

**RP5-B:**
```bash
cd /home/test2/Facebook-Denoiser-in-Raspberry-Pi-5
source venv_denoiser/bin/activate
python demo/duplex/start_debug_b.py
```

---

## 🎯 테스트 체크리스트

**1단계: 시작**
- [ ] RP5-A 실행됨
- [ ] RP5-B 실행됨
- [ ] 양쪽 모두 "🔄 Full-duplex DEBUG communication started" 출력

**2단계: 패킷 전송**
- [ ] TX > 0 (송신 카운트 증가)
- [ ] RX > 0 (수신 카운트 증가)
- [ ] TX ≈ RX (비슷한 수)

**3단계: 데이터 확인 (50번 패킷마다 디버그 출력)**
- [ ] TX DEBUG: packet size = 40-50 bytes
- [ ] RX DEBUG: received packet size = 40-50 bytes
- [ ] RX DEBUG: decoded abs_max > 0.1 (말할 때)

**4단계: 소리 확인**
- [ ] RP5-A 마이크에 말하기 → RP5-B 스피커에서 들림
- [ ] RP5-B 마이크에 말하기 → RP5-A 스피커에서 들림

---

## ✅ 성공 = 다음 단계

통신이 정상 작동하면:
1. 데이터 타입 수정 검증 완료
2. 기존 `rp5_full_duplex.py`에 적용
3. AI toggle 기능 복원

---

## ❌ 실패 = 디버그

소리가 안 들리면 `DEBUG_USAGE_GUIDE.md` 참조:
- 패킷 크기 확인
- 데이터 레벨 확인
- 네트워크 연결 확인

---

**소요 시간**: 총 5분
**난이도**: ⭐⭐☆☆☆
