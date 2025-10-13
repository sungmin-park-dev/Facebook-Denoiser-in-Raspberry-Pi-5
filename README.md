# 라즈베리파이 5 실시간 음성 디노이징 프로젝트 - 통합 지침서 v4.2
- 최종 업데이트: 2025-10-10
- 작성자: David(박성민) & Claude
- 상태: Migration 완료 (Mac), Colab 훈련 준비 중

## 1. 프로젝트 개요
- 목표: **라즈베리파이 5(RP5)**에서 실시간 음성 디노이징 시스템 구현
    - RTF < 1.0 달성 (처리시간/오디오길이)
    - 품질: PESQ > 2.5, STOI > 0.85
    - 경량: 모델 < 5MB, 메모리 < 1GB
- 기술 스택
  - 원본 (2020): PyTorch 1.5, torchaudio 0.5, Hydra 0.11
  - 현재 (Migration 완료): PyTorch 2.8.0, torchaudio 2.8.0, Hydra 1.1+, Python 3.12


## 2. 개발 환경 (3-Tier)

### 환경별 역할 구분
| | **맥북 🍎** | **Colab ☁️** | **RP5 🔧** |
| :--- | :---: | :---: | :---: |
| **설정 관리** | ✅ | ❌ | ❌ |
| **Debug 테스트** | ✅ | ✅ | ❌ |
| **Valentini 훈련** | ❌ | ✅ | ❌ |
| **RTF 테스트** | ❌ | ❌ | ✅ |
| **실시간 구동** | ❌ | ❌ | ✅ |

#### 맥북 (설정 관리 허브)

- 역할: 설정 파일 관리, 코드 수정, GitHub 동기화
- 환경: Apple M1, macOS 15.6.1, Python 3.12 (conda: denoiser_modern)
- 경로: /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5
- 상태: ✅ Migration 완료, Debug 훈련 성공 (STOI=0.8054)

- 환경 활성화:
```
conda activate denoiser_modern
cd /Users/david/GitHub/Facebook-Denoiser-in-Raspberry-Pi-5
```

#### Colab (훈련 전용)

- 역할: Valentini 데이터셋 본격 훈련 (4-8시간)
- 환경: GPU 필수, Python 3.10+, Google Drive 연동
- 상태: ⏳ 준비 중
- 주의: 중간 체크포인트 저장 필수

#### 라즈베리파이 5 (배포 및 실행)

- 역할: 최종 모델 검증 및 실시간 구동
- 환경: Cortex-A76 4코어, Ubuntu, CPU only
- 경로: /home/test1/denoiser
- 상태: ✅ RTF 최적화 완료 (Light-32-Depth4, RTF=0.834)


## 3. 프로젝트 진행 상황
### Phase 1: RTF 최적화 ✅ 완료 (RP5)
| 모델 | RTF | 크기 | 상태 |
|------|-----|------|------|
| **Light-32-Depth4** | **0.834** | **1.7MB** | ✅ **최적** |
| Light-40 | 0.905 | 2.6MB | ✅ 대안 |
| Standard-Light-48 | 1.167 | 3.7MB | ⚠️ 경계선 |

- 핵심 파라미터:
    - hidden=32, depth=4, resample=2 (핵심!)
    - glu=false, growth=1.5
    - kernel_size=8, stride=4 (변경 금지)


### Phase 2: Migration 및 Debug 훈련 ✅ 완료 (Mac)
- 주요 수정 사항:
  1. Hydra 1.1+ 호환 (train.py)
    - 문제: Hydra 0.11 문법이 1.1+에서 작동 안함
    - 해결: decorator 변경
    - 이유: Hydra 1.0+는 config_path에 디렉토리만, config_name에 파일명 분리

    ```
    # 수정 전
    @hydra.main(config_path="conf/config.yaml")

    # 수정 후
    @hydra.main(config_path="conf", config_name="config", version_base="1.1")
    ```

  2. Config 구조 변경 (conf/config.yaml)- 문제: defaults 로딩 순서 문제
    - 해결: _self_ 추가 및 override 키워드 사용
    - 이유: _self_가 없으면 현재 config가 덮어씌워짐
    ```
    defaults:
    - dset: debug
    - override hydra/job_logging: colorlog
    - override hydra/hydra_logging: colorlog
    - _self_
    ```
  
  3. Dataset YAML 구조 변경 (conf/dset/*.yaml)
    - 문제: dset: 키가 중복 네임스페이스 생성
    - 해결: dset: 키 완전 제거, 들여쓰기 0칸
    - 이유: Hydra가 - dset: debug로 로드 시 자동으로 args.dset 네임스페이스 할당
    ```
    # 수정 전
    dset:
      train: egs/debug/tr
      matching: sort
    # 수정 후
    train: egs/debug/tr
    matching: sort
    ```
    

  4. torchaudio API 변경 (denoiser/audio.py)
    - 문제: offset 파라미터가 2.8.0에서 제거됨
    - 해결: 모든 offset → frame_offset 변경
    - 이유: torchaudio 2.x에서 파라미터명 통일
    - 결과: Debug 훈련 성공 (1분, STOI=0.8054, best.th 72MB 생성)


### Phase 3: Colab Debug 테스트 ✅ 완료 (Colab)
- 목표: Colab 환경에서 훈련 가능 여부 검증
- 완료 날짜: 2025-10-13
- 결과:
  - setup.py 수정: hydra_core>=1.3.2, torch>=2.0 반영
  - requirements.txt 업데이트: Mac/Colab 버전 통일
  - Debug 훈련 성공: 2 epochs, 3분 소요
  - **STOI: 0.8056** (목표 0.75 초과 달성) ✅
  - **PESQ: 1.25** (Debug용, 본 훈련 아님)
  - Git commit: cf731606
- 핵심 해결:
  - pip install -e . 시 Hydra 다운그레이드 문제 해결
  - Mac-Colab 환경 완전히 통일 (Hydra 1.3.2, PyTorch 2.8.0)


### Phase 4: Valentini 본격 훈련 📋 다음 단계 (Colab)
- 목표: Light-32-Depth4 모델로 Valentini 데이터셋 훈련
- 사전 준비:
  - Valentini 데이터셋 Google Drive 업로드 필요
  - 데이터셋 경로 확인: `/content/drive/MyDrive/Colab Notebooks/ARMY Projects/valentini_dataset/`
  - conf/dset/valentini.yaml 설정 확인
- 훈련 설정:
  - epochs=100, batch_size=16, device=cuda
  - Light-32-Depth4 파라미터 (hidden=32, depth=4, resample=2, glu=false)
  - 중간 저장: 10 epoch마다 체크포인트
- 예상 결과:
  - 훈련 시간: 4-8시간 (GPU T4 기준)
  - 목표: PESQ > 2.5, STOI > 0.85
  - 모델 크기: ~2-3MB

- 주의사항:
    - GPU 사용 권장
    - Deprecation warnings 무시 가능
    - 실패 시 에러 로그 확인 후 재시도


### Phase 4: Valentini 본격 훈련 📋 예정 (Colab)
- 사전 준비:
    - Valentini 불러오기: 사전에 Google drive에 저장해둠
    - Valentini 데이터셋 경로:
      - Google Drive 원본: `/content/drive/MyDrive/Colab Notebooks/ARMY Projects/valentini_dataset/original_dataset`
      - 변환된 데이터: `.../converted_data`
      - Denoiser 작업 폴더: `/content/denoiser/dataset/valentini/`


- 훈련 설정:
    - epochs=100, batch_size=16, device=cuda
    - Light-32-Depth4 파라미터 적용
    - 중간 저장: 10 epoch마다 Drive 백업

- 예상 결과:
  - 훈련 시간: 4-8시간 (GPU T4)
  - PESQ > 2.5, STOI > 0.85 목표
  - 모델 크기: ~2-3MB


### Phase 5: RP5 배포 📋 예정
- 작업 순서:
  1. Colab → Drive → 로컬 → USB → RP5 전달
  2. RTF 재검증 (목표: 0.6-0.9)
  3. 품질 평가 (PESQ/STOI)
  4. 실시간 디노이징 테스트

- 검증 명령어 (확인 필요):
```
python rpi5_optimization/quick_rtf_test.py --model_path trained_models/valentini_light32.th
python -m denoiser.evaluate --model_path trained_models/valentini_light32.th --data_dir test_data/
python -m denoiser.live --model_path trained_models/valentini_light32.th --device cpu
```

## 4. 핵심 인사이트

- 성능 영향 요소 (과거 RP5벤치마킹을 기반으로한 결과)
  - resample=2 ⭐⭐⭐⭐⭐
    - 4→2 변경 시 2.5배 성능 향상 (가장 큰 영향)
  - hidden=32 ⭐⭐⭐⭐⭐
    - 48→32 감소 시 28% 성능 개선
  - depth=4 ⭐⭐⭐⭐
    - 5→4 감소 시 28% 성능 개선
  - glu=false ⭐⭐⭐
    - 파라미터 50% 감소, 품질 영향 미미
  - growth=1.5 ⭐⭐⭐
    - 2.0→1.5 경량화, max_hidden=128과 함께 사용

- 변경 금지 파라미터
  - kernel_size=8, stride=4: Demucs 핵심 설계, 변경 시 품질 저하
  - 스트리밍 방식 RTF 측정 필수: 배치 처리는 비현실적 (0.3-0.4)


## 6. 다음 단계 체크리스트
### 완료 (2025-10-13)
- Phase 1: RTF 최적화 (RP5)
- Phase 2: Migration 및 Debug 훈련 (Mac)
- Phase 3: Colab Debug 테스트** 🎉
  - setup.py 수정 (Hydra 1.3.2+ 호환)
  - requirements.txt 업데이트
  - Debug 훈련 성공 (STOI=0.8056)
  - Git commit & push (cf731606)

### ⏳ 진행 예정
- **즉시 시작 (Phase 4):**
  - [ ] Valentini 데이터셋 Google Drive 업로드 확인
  - [ ] conf/dset/valentini.yaml 수정 (경로 확인)
  - [ ] Colab 노트북 작성 (valentini_training.ipynb)
  - [ ] 본격 훈련 시작 (100 epochs, 4-8시간)

- **병렬 진행:**
  - [ ] 중간 체크포인트 모니터링 (10 epoch마다)
  - [ ] PESQ/STOI 추이 확인
  - [ ] Google Drive 백업 설정


- 본 훈련 (4-8시간):
  - Colab Valentini 훈련
  - 중간 저장 설정
  - PESQ/STOI 확인

- 배포 (2-3시간):
  - RP5 전달 및 RTF 재검증
  - 실시간 디노이징 테스트


## 7. 단계별 성공 기준
### Phase 3 (Colab Debug)
- Debug 훈련 성공
- STOI > 0.75
- 에러 없이 완료

### Phase 4 (Valentini 훈련)
- 100 epoch 완료
- PESQ > 2.5 (인간 청취 인식 수준)
- STOI > 0.85 (명료도 85%)
- 모델 크기 < 5MB

### Phase 5 (RP5 배포)
- RTF < 1.0 (실시간 처리)
- 추가 확인하면 좋은 사항: 메모리 저부하, 온도 안정, 장시간 무오류 구동

### 최종 목표
- RTF: 0.6-0.9 (RP5 스트리밍)
- PESQ: > 2.5 (목표: 2.8-3.2)
- STOI: > 0.85 (목표: 0.88-0.92)
- 모델: < 3MB, 메모리: < 500MB, 레이턴시: < 100ms


## 8. 참고 링크
- 프로젝트:
  - GitHub: https://github.com/sungmin-park-dev/Facebook-Denoiser-in-Raspberry-Pi-5
  - 원본: https://github.com/facebookresearch/denoiser
  - 논문: https://arxiv.org/abs/2006.12847

- 데이터셋:
  - Valentini: https://datashare.is.ed.ac.uk/handle/10283/2791
- 문서:
  - Hydra 1.1: https://hydra.cc/docs/upgrades/1.0_to_1.1/changes_to_default_composition_order
  - PyTorch: https://pytorch.org/docs/stable/
  - torchaudio: https://pytorch.org/audio/stable/


## 9. FAQ
- Q: 왜 맥북에서 훈련 안하나요?
- A: Colab GPU가 3-5배 빠르고 무료입니다.
- Q: RTF=0.834가 의미하는 것은?
- A: 4초 오디오를 3.3초에 처리. RTF < 1.0이면 실시간 가능.
- Q: PESQ > 2.5면 좋은건가요?
- A: PESQ는 1.0(최악)~4.5(완벽). 2.5는 "양호", 3.0 이상이면 "우수".
- Q: 양자화는 언제 하나요?
- A: Phase 5 이후. FP32 품질 확보 후 INT8 양자화 적용.

| 버전 | 날짜 | 변경사항 |
|------|------|----------|
| v1.0 | 2025-01-08 | 초기 계획 |
| v2.0 | 2025-01-09 | RTF 최적화 완료 |
| v3.0 | 2025-01-10 | Migration 완료 |
| v4.1 | 2025-01-11 | 간결화 (클로드 가독성 중심) |
| **v4.2** | **2025-01-13** | **Phase 3 완료, Phase 4 준비** |

**v4.2 주요 변경:**
- setup.py 수정: Hydra/PyTorch 버전 업데이트
- requirements.txt 통일: Mac/Colab 동일 환경
- Colab Debug 테스트 완료: STOI=0.8056
- Git commit: cf731606 (setup.py, requirements.txt)


### 핵심 원칙:
- 환경 분리 (Mac-Colab-RP5 역할 혼동 금지)
- 단계별 검증 (Debug → Valentini → 배포)
- 품질 우선 (성능보다 품질 먼저)
- 문서화 (변경사항 기록)
