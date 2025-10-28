# 🎖️ Combat Audio Synthesis & Comparison

전장 노이즈 합성 및 디노이징 성능 비교 도구

---

## 📁 구조
```
demo/audio_comparison/
├── scenario_configs/           # 전장 시나리오 JSON 설정
│   ├── final4_multi_heli.json        # 다중 헬기 (20초) ⭐
│   └── final4_multi_heli_60s.json    # 다중 헬기 (60초) ⭐
├── samples/
│   ├── sound_effects/          # 전투 효과음 (사용자 준비)
│   ├── clean_speech/           # 깨끗한 음성 입력
│   ├── noisy/                  # 합성된 노이즈 음성
│   ├── classical/              # 고전 방법 결과
│   └── denoiser/               # AI 방법 결과
├── preview_sound_effects.py    # 전투 노이즈 생성
├── synthesize_combat_audio.py  # 음성 + 노이즈 합성
└── denoise_classical.py        # 고전 디노이징
```

---

## 🚀 사용법

### 1. 효과음 준비
다운로드: [Freesound.org](https://freesound.org)

필요한 파일 (예시):
- `Rain_and_Thunderstorm_sound.mp3`
- `Apache_helicopter.mp3`
- `War Zone Ambience Sound Effect.mp3`
- `Bomb sound.mp3`
- `WW1_Trench+Rain.mp3`
- `Ukraine_War_in_Winter.mp3`

저장 위치: `samples/sound_effects/`

### 2. 전투 노이즈 미리듣기
```bash
python demo/audio_comparison/preview_sound_effects.py
```

### 3. 음성 + 노이즈 합성
```bash
# 음성 파일 준비
cp your_voice.wav samples/clean_speech/

# 합성 실행
python demo/audio_comparison/synthesize_combat_audio.py
```

**설정** (`synthesize_combat_audio.py`):
```python
SCENARIO_CONFIG = "scenario_configs/final4_multi_heli.json"  # 시나리오 선택
TARGET_SNR_DB = 5  # SNR 설정 (5dB 추천)
```

### 4. 디노이징 비교
```bash
# 고전 방법
python demo/audio_comparison/denoise_classical.py \
    --input samples/noisy \
    --output samples/classical

# AI 방법 (메인 denoiser 사용)
python -m denoiser.enhance \
    --dns48 \
    samples/noisy \
    --out samples/denoiser
```

---

## 🎯 시나리오 추천

| 시나리오 | 길이 | 특징 | 추천 |
|---------|------|-----|------|
| `final4_multi_heli` | 20초 | 다중 헬기, 균형 | ⭐⭐⭐ |
| `final4_multi_heli_60s` | 60초 | 강도 변화, 다이내믹 | ⭐⭐⭐⭐⭐ |
| `final5_complete_warzone_60s` | 60초 | 복잡도 최고 | ⭐⭐⭐⭐ |

---

## 📊 파라미터 가이드

### SNR (Signal-to-Noise Ratio)
- `10 dB`: 중간 난이도
- `5 dB`: 어려움 (전투 상황, **추천**)
- `3 dB`: 매우 어려움
- `0 dB`: 극도로 어려움

### Duration 조정
```python
# preview_sound_effects.py
DURATION = 60  # 60초로 변경 (자동 스케일링)
```

---

## 🔧 커스터마이징

### 새 시나리오 만들기
1. `scenario_configs/` 폴더에 JSON 파일 생성
2. 기존 파일 참고하여 작성
3. 효과음 타이밍/볼륨 조정

### JSON 구조
```json
{
  "name": "my_scenario",
  "description": "설명",
  "duration": 20,
  "effects": {
    "effect_name": {
      "file": "sound.mp3",
      "type": "continuous|segment|impulse",
      "volume": 0.5,
      "timings": [3.0, 7.0]  // impulse만
    }
  }
}
```

---

## 📝 Notes

- 오디오 파일은 Git에서 제외됨 (`.gitignore`)
- 샘플링 레이트: 16kHz (고정)
- 권장 SNR: 5dB (전투 상황)
- 권장 시나리오: `final4_multi_heli_60s`