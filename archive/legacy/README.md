# Legacy Code Archive

이 폴더에는 프로젝트 개발 과정에서 사용되었지만 현재는 `demo/` 디렉토리의 모듈화된 시스템으로 대체된 레거시 코드들이 보관되어 있습니다.

## 📁 폴더 구조

### early_realtime/
초기 실시간 디노이징 시스템 프로토타입

| 파일 | 설명 | 대체됨 |
|------|------|--------|
| `test_realtime.py` | 버퍼 기반 실시간 스트리밍 | `demo/duplex/rp5_full_duplex_modular.py` |
| `test_realtime_original.py` | Facebook 원본 모델 테스트 (dns48/dns64) | `demo/duplex/processors/` |
| `demo_ai_toggle_simple.py` | AI on/off 토글 데모 | `demo/duplex/` 토글 시스템 |

**특징:**
- Phase 6 시절의 단일 파일 구현
- 단순 로컬 처리 (네트워크 없음)
- 토글 기능 제한적

**왜 대체되었나:**
- Duplex 시스템이 모듈화, WiFi 통신, 프로세서 토글 모두 지원
- 더 나은 아키텍처 (core + processors 분리)

---

### utilities/
일회성 유틸리티 스크립트

| 파일 | 설명 | 용도 |
|------|------|------|
| `check_audio_device.py` | 오디오 디바이스 확인 | 디버깅/설정 |
| `find_available_device.py` | 사용 가능한 디바이스 찾기 | 중복 (check_audio_device와 동일) |
| `process_audio.py` | 오프라인 .wav 파일 처리 | 4단계 필터 체인 테스트용 |

**특징:**
- 독립 실행 스크립트
- 한번 사용 후 보관

---

### dataset_conversion/
데이터셋 변환 스크립트 (한번 실행)

| 파일 | 설명 | 상태 |
|------|------|------|
| `convert_sample_files.py` | 샘플 파일 48kHz → 16kHz (5개씩) | 완료 |
| `convert_full_valentini.py` | 전체 Valentini 데이터셋 변환 | 완료 |

**용도:**
- Valentini 데이터셋을 16kHz로 리샘플링 (훈련 전 준비)
- 이미 실행 완료, 재사용 불필요

---

## 🔗 현재 시스템

모든 기능은 다음으로 통합되었습니다:

```
demo/
├── duplex/                      # ★ Full-Duplex WiFi 통신
│   ├── core/                    # 통신 + 처리 모듈
│   ├── processors/              # AI/Bypass/Filters (토글 가능)
│   └── start_modular_a.py       # 실행 스크립트
├── duplex_macbook_hotspot/      # MacBook Hotspot 버전
└── simplex/                     # 단방향 통신
```

**왜 더 나은가:**
- ✅ 모듈화 아키텍처 (유지보수 용이)
- ✅ WiFi Direct 양방향 통신
- ✅ 런타임 프로세서 전환 (Bypass ↔ AI ↔ Filters)
- ✅ CPU Performance 모드 통합
- ✅ 설정 파일 기반 (YAML)

---

## ⚠️ 주의사항

이 폴더의 코드는:
- **보관 목적**으로만 유지됨
- 실행 가능하지만 **사용 권장하지 않음**
- Git 히스토리 보존을 위해 `git mv`로 이동됨

---

**보관일**: 2025-11-26
**이유**: Phase 7 Full-Duplex 시스템으로 대체
