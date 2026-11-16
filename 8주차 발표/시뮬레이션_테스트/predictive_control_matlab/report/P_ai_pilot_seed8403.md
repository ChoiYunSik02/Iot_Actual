# 8주차 소규모 AI 학습 (PyTorch, seed 8403)

- 실행: MATLAB 26.1.0.3346908 (R2026a) Update 5, 커밋 `e0b8c66f6207f2b9d2972933b20468406e5a66ba`, 코드 digest `081c113e74092a56`, 설정 `c6e7b9c6838848de`
- Python 3.11, torch 2.6.0+cu124, 장치 cuda
- **범위를 제한한 탐색적 학습입니다.** 구조 탐색 없음. 학습·검증·체크포인트 선택은 합성 자료만 사용, 실제 기록은 학습 후 진단에만 사용.
- 학습 전 점검: 64창 과적합 시험 손실 1.2955 → 0.2142 (통과), 정답 무진동(RMS<0.1) 창 비율 0.169

| 항목 | 값 |
|---|---|
| 자료 | `build_forecast_dataset('pilot')`, 학습 창 32000, 검증 창 8000, 해시 `2c37c5981892d318` |
| 학습 | 최대 100 epoch, 종료 epoch 15 (최저 검증), 검증 MSE 1.0648, 115 s |
| 출력 일치 | Python 대 MATLAB 재구현 6.9e-07 |

예측 RMSE (m/s², 사건 평균): `results/forecast_metrics_pilot_torch.csv`

| 자료 | 예측기 | 0.2 s | 1 s | 4 s |
|---|---|---|---|---|
| val | zero | 0.0664 | 0.0701 | 0.0654 |
| val | persistence | 0.0704 | 0.0941 | 0.0933 |
| val | lstmnat | 0.0528 | 0.0667 | 0.0645 |
| real_val | zero | 0.0229 | 0.0262 | 0.0248 |
| real_val | persistence | 0.0296 | 0.0349 | 0.0340 |
| real_val | lstmnat | 0.0213 | 0.0262 | 0.0249 |

예측 계산시간(MATLAB 재구현): `logs/runtime_measure_pilot8_seed8403.csv`, 학습 곡선: `models/torch_pilot8_seed8403.json` history
