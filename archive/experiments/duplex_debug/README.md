# Archive - Legacy Versions

## 📁 Directory Structure

### `v1_working/`
**이전 작동 버전** (2025-11-03 ~ 2025-11-13)
- WiFi Direct 양방향 통신 성공
- AI 디노이징 기능 포함
- 단일 파일 구조 (통신 + AI 로직 혼재)

**파일:**
- `rp5_full_duplex.py` - 메인 스크립트
- `start_full_duplex_a.py` - RP5-A 실행 스크립트
- `start_full_duplex_b.py` - RP5-B 실행 스크립트
- `docs/` - 관련 문서

**특징:**
✅ 양방향 통신 작동
✅ AI 디노이징 작동
❌ 코드 구조 복잡 (통신 + AI 혼재)
❌ 프로세서 토글 불가능

---

### `debug/`
**디버그 버전** (2025-11-13 ~ 2025-11-14)
- 통신 문제 해결용 간소화 버전
- AI 기능 제거, 통신 로직만 포함
- Opus 코덱 버그 발견 및 해결

**파일:**
- `rp5_full_duplex_debug.py` - 디버그 메인
- `start_debug_a.py`, `start_debug_b.py` - 실행 스크립트
- `rp5a_debug.yaml`, `rp5b_debug.yaml` - 설정 파일
- `test_opus_codec.py` - 코덱 테스트
- `DEBUG_USAGE_GUIDE.md` - 사용 가이드

**특징:**
✅ 통신 문제 해결 (float32 직접 전달)
✅ 간단한 구조
❌ AI 기능 없음

---

## 🚀 현재 버전 (Modular)

**경로:** `demo/duplex/`
- 모듈화 아키텍처
- 런타임 프로세서 토글
- 확장 가능한 구조

**현재 파일:**
```
demo/duplex/
├── core/               # 통신 로직
├── processors/         # 오디오 프로세서
├── rp5_full_duplex_modular.py
└── configs/
    ├── rp5a_modular.yaml
    └── rp5b_modular.yaml
```

---

## 📅 버전 히스토리

| 버전 | 기간 | 상태 | 위치 |
|------|------|------|------|
| **V2 Modular** | 2025-11-15 ~ | ✅ Current | `demo/duplex/` |
| V1 Working | 2025-11-03 ~ 2025-11-14 | 📦 Archived | `archive/v1_working/` |
| Debug | 2025-11-13 ~ 2025-11-14 | 📦 Archived | `archive/debug/` |

---

## 💡 참고

**복원 방법:**
```bash
# V1 복원 (필요 시)
cp archive/v1_working/rp5_full_duplex.py .
cp archive/v1_working/start_full_duplex_*.py .

# Debug 복원 (필요 시)
cp archive/debug/rp5_full_duplex_debug.py .
cp archive/debug/start_debug_*.py .
```

**보관 날짜:** 2025-11-15
