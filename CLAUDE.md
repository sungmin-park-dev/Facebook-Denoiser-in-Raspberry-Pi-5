이 Claude.ai 대화를 참조해서 작업을 진행해줘:

https://claude.ai/chat/cd99d820-b4fb-452a-a09e-48064d693382

# 프로젝트 정보

- 경로: /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5

- 현재 브랜치: main

- 프로젝트: RP5 실시간 음성 디노이징 시스템

# 작업 목표

GitHub 폴더 구조 정리 및 문서 통합

## 구체적 작업 내용

### 1. demo/simplex 확인

- Import 경로 체크

- 실행 가능 여부 확인

- 판단: 곧바로 사용 가능하면 유지, 불가능하면 archive/experiments/로 이동

### 3. demo/duplex_macbook_hotspot/ 추가 생성

- demo/duplex/ 전체를 demo/duplex_macbook_hotspot/로 복사

- configs/ 내 파일명 변경:

  - rp5a_config.yaml → rp5a_macbook.yaml

  - rp5b_config.yaml → rp5b_macbook.yaml

- 설정 파일 내용 수정:

  - peer_ip를 맥북 핫스팟 대역(192.168.2.x)으로 변경

  - 주석으로 "MacBook Hotspot Configuration" 추가

- README.md 작성 (맥북 핫스팟 설정 가이드)

### 4. archive 정리

- demo/duplex/archive/ 내용을 archive/experiments/duplex_debug/로 이동
- demo/duplex/archive/ 폴더 삭제
- 기타 정리가능 파일 또는 폴더 발견시 선 보고 후 답변에 따라 조치

### 5. 중복 MD 파일 통합

다음 문서들을 통합하고 간결하게 재작성:
- docs/PHASE2_SUCCESS.md + demo/duplex/docs/PHASE2_SUCCESS.md
  → docs/COMPLETED_PHASES.md
- demo/duplex/docs/MODULAR_ARCHITECTURE.md + DIRECTORY_STRUCTURE.md
  → docs/ARCHITECTURE.md
- demo/duplex/docs/CPU_PERFORMANCE_GUIDE.md
  → docs/SETUP_GUIDE.md에 통합
통합 후 원본 파일들은 삭제

### 5. 최상위 README.md 업데이트
- 새 폴더 구조 반영
- demo/duplex와 demo/duplex_macbook_hotspot 차이 명시
- Quick Start 섹션 업데이트

## 제약사항 (중요!)
- ✅ demo/duplex는 유지 (삭제하지 말것): 토글 기본 설정 변경! --- rp5a는 AP, bypass(denoising off), rp5b는 client, denoising on
- ✅ demo/Mac_and_bluetooth_speaker_realtime 유지

- ❌ denoiser/, conf/, train.py 등 원본 Facebook 코드 변경 금지

- ❌ models/ 폴더 변경 금지

- ✅ Git 명령어 사용 (git mv)로 히스토리 보존

## 작업 순서

1. 먼저 전체 파일 구조 확인 후 계획 알려주기

2. 내 승인 후 단계별 실행

3. 각 단계마다 결과 요약

4. 마지막에 git add/commit 명령어 제안

작업 시작 전에 현재 폴더 구조를 먼저 보여줘.