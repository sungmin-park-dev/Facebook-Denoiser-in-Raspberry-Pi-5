# AI 양방향 통신 디버깅 실험 기록

## 문제 정의
- 증상: AI 모드에서 음성 94% 제거
- 확인: AI 단독 OK, Duplex 단독 OK, 조합 실패
- 가설: Opus 코덱 또는 AI 처리 순서 문제

## 실험 목록

### 실험 A: 수신측 AI 이동 [READY]
- 목적: Opus 후 AI 처리
- 파일: rp5_full_duplex_modular.py
- 상태: 코드 준비 완료

### 실험 B: Opus bitrate 증가 [PENDING]
- 목적: 압축 품질 개선
- 파일: audio_comm.py

## 실험 결과
[여기에 결과 추가]
