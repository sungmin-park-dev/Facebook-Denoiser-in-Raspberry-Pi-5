# 프로젝트 정보

- **경로**: /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5
- **현재 브랜치**: main
- **프로젝트**: RP5 실시간 음성 디노이징 시스템
- **상태**: Phase 7 완료, v6.1 (2025-12-06)
- **최신 커밋**: d09dab15 - Project reorganization and documentation consolidation

---

# ✅ 완료된 작업 (2025-12-06)

## demo/duplex_public_wifi 전환 (v6.1)

### 배경
- MacBook Hotspot이 macOS Sequoia 15.6.1 버그로 작동하지 않음
- 공용 WiFi (Welcome_KAIST) 방식으로 변경 결정
- 테스트 완료: MacBook ↔ RP5-B 양방향 통신 성공
  - 서로 다른 서브넷 (10.249.55.x ↔ 10.249.98.x)에서도 작동 확인
  - 패킷 손실: 0%, 평균 지연: 35-40ms

### 주요 변경 사항

#### 1. ✅ Config 파일 이름 변경 및 업데이트
- `rp5a_macbook.yaml` → `rp5a_public.yaml` (git mv)
- `rp5b_macbook.yaml` → `rp5b_public.yaml` (git mv)
- peer_ip를 mDNS (hostname.local) 기본값으로 변경
- IP 대역 예시: 192.168.2.x → 10.249.x.x로 변경

#### 2. ✅ IP 동적 탐지 기능 구현 (start_modular_a.py, start_modular_b.py)
**4단계 Fallback 메커니즘:**
- 우선순위 1: 명령행 인자 (`--peer-ip`)
- 우선순위 2: mDNS hostname 해석 (socket.gethostbyname)
- 우선순위 3: 자동 탐지 (ping sweep)
- 우선순위 4: 대화형 수동 입력 (IP 검증 포함)

**추가 개선:**
- 경로 버그 수정: `demo/duplex/` → `demo/duplex_macbook_hotspot/` (Line 333)
- `argparse` 추가: `--peer-ip`, `--config` 옵션 지원
- Public WiFi 체크 함수로 변경 (WiFi Direct 체크 제거)
- Client Isolation 경고 메시지 추가

#### 3. ✅ README.md 전면 재작성 (335 lines)
- Public WiFi 기반 설정 가이드
- IP 동적 할당 해결 방법 상세 설명 (mDNS, 자동 탐지, 수동 입력)
- Client Isolation 확인 필수 강조
- 서브넷 간 통신 가능 설명 추가
- MacBook Hotspot 관련 모든 내용 제거
- duplex vs duplex_macbook_hotspot 비교 표 추가

### 파일 변경 목록
```
demo/duplex_macbook_hotspot/ → demo/duplex_public_wifi/ (디렉토리 이름 변경)
├── configs/
│   ├── rp5a_macbook.yaml → rp5a_public.yaml
│   └── rp5b_macbook.yaml → rp5b_public.yaml
├── start_modular_a.py (IP 탐지 로직 추가, 경로 수정)
├── start_modular_b.py (IP 탐지 로직 추가, 경로 수정)
└── README.md (전면 재작성)
```

---

# ✅ 완료된 작업 (2025-11-26)

## 프로젝트 정리 완료 (v6.0)

### 1. ✅ demo/simplex 확인 및 유지
- Import 경로 검증 완료 (모든 의존성 존재)
- 실행 가능 확인
- **결정**: 유지 (변경 없음)

### 2. ✅ demo/duplex_public_wifi/ 생성 (이전 duplex_macbook_hotspot)
- demo/duplex/ 전체 복사 완료
- configs 파일명 변경: rp5a_public.yaml, rp5b_public.yaml
- IP 대역: DHCP 동적 할당 (Public WiFi)
- README.md 작성 완료 (Public WiFi 설정 가이드)

### 3. ✅ Archive 정리
- demo/duplex/archive/ → archive/experiments/duplex_debug/ 이동 (git mv)
- 개발 히스토리 보존 (debug, v1_working, v2_baseline)

### 4. ✅ 중복 문서 통합
**생성된 통합 문서:**
- `docs/ARCHITECTURE.md` - 시스템 아키텍처 (MODULAR_ARCHITECTURE + DIRECTORY_STRUCTURE 통합)
- `docs/SETUP_GUIDE.md` - 설치 및 CPU 설정 (CPU_PERFORMANCE_GUIDE + 환경 설정 통합)
- `docs/COMPLETED_PHASES.md` - Phase 완료 기록 (PHASE2_SUCCESS 이름 변경)

**삭제된 중복 파일:**
- DIRECTORY_STRUCTURE.md (최상위)
- demo/duplex/docs/MODULAR_ARCHITECTURE.md
- demo/duplex/docs/CPU_PERFORMANCE_GUIDE.md
- demo/duplex/outputs/*.md (4개 파일)

### 5. ✅ 레거시 코드 정리
**archive/legacy/ 구조:**
- early_realtime/ - 초기 실시간 스크립트 3개
- utilities/ - 유틸리티 스크립트 3개
- dataset_conversion/ - 데이터셋 변환 스크립트 2개
- benchmarks/ - RTF 테스트 결과

### 6. ✅ Requirements 통합
- requirements.txt 통합 및 문서화 (크로스 플랫폼 호환)
- requirements_mac_rpi.txt → archive/legacy/ 이동

### 7. ✅ README.md 업데이트
- v6.0 상태 반영
- duplex vs duplex_macbook_hotspot 비교 표 추가
- Quick Start 섹션 업데이트
- 버전 히스토리 추가

---

# 📁 현재 프로젝트 구조

```
Facebook-Denoiser-in-Raspberry-Pi-5/
├── train.py, setup.py, hubconf.py      # 핵심 파일 (변경 금지)
├── requirements.txt                     # 통합 (v6.0)
├── launch_*.sh, make_debug.sh           # Facebook 훈련 스크립트 (유지)
│
├── demo/
│   ├── duplex/                          # WiFi Direct (10.42.0.x) - 운영 환경
│   ├── duplex_public_wifi/              # Public WiFi (DHCP, mDNS 지원) - 테스트/개발
│   ├── simplex/                         # 단방향 통신
│   └── Mac_and_bluetooth_speaker_realtime/
│
├── docs/                                # 통합된 문서 3개
│   ├── ARCHITECTURE.md
│   ├── SETUP_GUIDE.md
│   └── COMPLETED_PHASES.md
│
├── archive/
│   ├── experiments/duplex_debug/        # Duplex 개발 히스토리
│   └── legacy/                          # 레거시 코드 (8 Python files)
│
├── models/                              # AI 모델 (변경 금지)
├── denoiser/                            # Facebook 원본 코드 (변경 금지)
└── conf/                                # Hydra 설정 (변경 금지)
```

---

# 🎯 다음 작업 예정 (Task A/C)

## Task A: 4단계 필터 체인
- HPF (80Hz) + Impulse Suppressor + AI Denoiser + Soft Limiter
- src/filters/ 모듈 구현

## Task C: WiFi 통신 최적화
- src/communication/ 모듈 구현
- WiFi Direct 성능 개선

---

# ⚠️ 제약사항 (중요!)

## 절대 변경 금지
- ❌ denoiser/ - Facebook 원본 코드
- ❌ conf/ - Hydra 설정
- ❌ train.py - 모델 훈련 스크립트
- ❌ models/ - AI 모델 체크포인트
- ❌ launch_*.sh, make_debug.sh - Facebook 훈련 스크립트

## 유지해야 할 폴더
- ✅ demo/duplex/ - WiFi Direct 메인 시스템
- ✅ demo/duplex_public_wifi/ - Public WiFi 테스트/개발용 (v6.1)
- ✅ demo/simplex/ - 단방향 통신
- ✅ demo/Mac_and_bluetooth_speaker_realtime/

## 작업 원칙
- ✅ Git 명령어 사용 (git mv)로 히스토리 보존
- ✅ 변경 전 사용자 승인 필요
- ✅ 단계별 결과 요약 제공

---

# 📚 참고 문서

- **전체 시스템**: README.md
- **아키텍처**: docs/ARCHITECTURE.md
- **설치/설정**: docs/SETUP_GUIDE.md
- **Phase 기록**: docs/COMPLETED_PHASES.md
- **Public WiFi**: demo/duplex_public_wifi/README.md
- **레거시 코드**: archive/legacy/README.md

---

**마지막 업데이트**: 2025-12-06
**버전**: v6.1
**상태**: Public WiFi 전환 완료 ✅