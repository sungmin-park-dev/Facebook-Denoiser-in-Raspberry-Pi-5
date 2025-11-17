# GitHub Commit Guide

## 프로젝트 정리 및 문서화 (대화 1)

### 커밋 구조

```bash
# 1. README 및 문서 추가
git add README.md
git commit -m "docs: Add comprehensive project documentation

- Phase 1-6 완료 내용 정리
- 성능 벤치마크 결과 (Light-32-Depth4: RTF 0.071)
- 원본 denoiser 모델 비교 (dns48, dns64 테스트 결과)
- Task A (필터 체인), Task C (WiFi 통신) 계획 추가
- 디렉토리 구조 및 설치 가이드"

# 2. .gitignore 추가
git add .gitignore
git commit -m "chore: Add .gitignore for Python and PyTorch projects

- Python cache 및 빌드 파일 제외
- 대용량 모델 파일 제외 (best.th 제외)
- 오디오 테스트 파일 제외"

# 3. 실시간 스크립트 정리
git add test_realtime.py
git commit -m "feat: Add Phase 6 real-time denoising with Light-32-Depth4

- 버퍼 기반 스트리밍 (2초 버퍼, 끊김 없음)
- 멀티스레드 처리 (입력/처리/출력 분리)
- H08A USB Audio 통합 (Device 1, 2채널)
- 성능: RTF 0.071, Latency ~2초
- 48kHz ↔ 16kHz 리샘플링"

# 4. 원본 denoiser 테스트 스크립트
git add test_realtime_original.py
git commit -m "test: Add original denoiser model benchmark script

- torch.hub 기반 모델 로딩 (dns48, dns64, master64)
- RP5 성능 테스트 결과:
  - dns48: RTF 1.484 (실시간 불가)
  - dns64: RTF 1.887 (실시간 불가)
- Light-32-Depth4가 RP5에 최적임을 확인"

# 5. 유틸리티 스크립트
git add utils/check_audio_device.py
git commit -m "feat: Add audio device capability checker

- sounddevice 디바이스 정보 조회
- H08A USB Audio 스펙 확인 도구
- 채널 수, 샘플레이트 자동 감지"

# 6. 전체 push
git push origin main
```

---

## 커밋 메시지 컨벤션

### 타입 (Type)
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅 (기능 변경 없음)
- `refactor`: 코드 리팩토링
- `test`: 테스트 코드 추가/수정
- `chore`: 빌드, 설정 파일 수정
- `perf`: 성능 개선

### 예시
```
feat: Implement 6-stage filter chain for tactical audio
fix: Resolve ALSA channel configuration error
docs: Update README with Task A implementation plan
refactor: Modularize AI model loading for easy switching
test: Add RTF benchmark for dns48 and dns64 models
chore: Update .gitignore for audio test files
perf: Optimize impulse noise suppressor (RTF 0.015 → 0.010)
```

---

## 브랜치 전략 (선택 사항)

### 메인 브랜치
```
main: 안정 버전 (Phase 6 완료)
```

### 개발 브랜치
```
feature/task-a-filters: Task A 필터 체인 개발
feature/task-c-wifi: Task C WiFi 통신 개발
```

### 워크플로우
```bash
# Task A 브랜치 생성
git checkout -b feature/task-a-filters

# 작업 후 커밋
git add filters/
git commit -m "feat: Add impulse noise suppressor"

# 완료 후 main에 병합
git checkout main
git merge feature/task-a-filters
git push origin main
```

---

## 현재 프로젝트 상태

### Git 초기화 (처음 한 번만)
```bash
cd /home/test1/denoiser

# Git 초기화
git init

# 원격 저장소 연결 (GitHub 주소로 변경)
git remote add origin https://github.com/username/rpi5-tactical-audio.git

# 첫 커밋
git add .
git commit -m "chore: Initial project setup with Phase 1-6"
git branch -M main
git push -u origin main
```

### 이미 Git 저장소가 있는 경우
```bash
# 현재 상태 확인
git status

# Phase 6 완료 커밋
git add test_realtime.py README.md
git commit -m "feat: Complete Phase 6 real-time streaming

- Light-32-Depth4 모델 통합
- RTF 0.071 달성 (실시간 14배 여유)
- 버퍼 기반 끊김 없는 스트리밍"

git push origin main
```

---

## 태그 (버전 관리)

```bash
# Phase 완료 시 태그 생성
git tag -a v0.6 -m "Phase 6: Real-time streaming completed"
git push origin v0.6

# Task A 완료 시
git tag -a v0.7 -m "Task A: 6-stage filter chain implemented"
git push origin v0.7

# Task C 완료 시
git tag -a v1.0 -m "v1.0: Full-duplex WiFi communication system"
git push origin v1.0
```

---

## 주의사항

### 대용량 파일
```bash
# models/best.th 파일이 크면 Git LFS 사용
git lfs install
git lfs track "*.th"
git add .gitattributes
git commit -m "chore: Add Git LFS for model files"
```

### 민감 정보
```bash
# WiFi 비밀번호, API 키 등은 .env 파일로 분리
echo "*.env" >> .gitignore
```

---

## 추천 커밋 순서 (대화 1)

```bash
# 1단계: 문서 및 설정
git add README.md .gitignore
git commit -m "docs: Project documentation and setup"

# 2단계: 핵심 코드
git add test_realtime.py test_realtime_original.py
git commit -m "feat: Real-time denoising scripts (Phase 6)"

# 3단계: 유틸리티
git add utils/check_audio_device.py
git commit -m "feat: Audio device checker utility"

# 4단계: 모델 (크기 확인 후)
# best.th가 GitHub 제한(100MB) 이하인 경우
git add models/best.th
git commit -m "model: Add Light-32-Depth4 checkpoint"

# Push
git push origin main
```

---

## 대화 2 (Task A) 준비

```bash
# 새 브랜치 생성
git checkout -b feature/task-a-filters

# 작업 진행...

# Task A 완료 후
git checkout main
git merge feature/task-a-filters
git tag -a v0.7 -m "Task A: Filter chain completed"
git push origin main --tags
```

---

**다음 대화에서 활용**: 이 가이드를 참고하여 Task A, C 완료 시 커밋
