# PyTorch LSTM smoke 학습·추론 연결 시험

- 실행: MATLAB 26.1.0.3346908 (R2026a) Update 5, 브랜치 `claude/focused-gauss-ubza04`, 커밋 `32836367349cfd92a1dbf0a6e625032af6b117a7`, 코드 digest `9f990f9278b3d820`
- Python 3.11 (`C:\Users\cys\AppData\Local\Programs\Python\Python311\python.exe`, OutOfProcess), torch 2.6.0+cu124
- **smoke 연결 시험입니다.** 정식 pilot이 아니며, 예측·제어 성능 주장에 쓰지 않습니다 (G2·G3 통과 후 pilot).

## 학습
- 자료: MATLAB `build_forecast_dataset('smoke')` 그대로 (합성 160/40, 분할 시드 8400, 생성 시드 84000~84199), 형식 matlab-v7.3, 해시 `5dfef938f516e1e5`
- 학습 창 14581, 검증 창 3695, 최대 10 epoch, 최저 검증 MSE 1.0057 (epoch 9), 학습 448 s (MATLAB에서 본 전체 455 s)
- Python 내부 numpy 순전파 대조 2.5e-07, MATLAB 재구현 대 Python 호출 5.1e-07

## 예측 진단
`results/forecast_metrics_smoke_torch.csv` (val = 합성 검증, real_val = 실제 개발 사건 El Centro·포항·고베)

## 실행시간
`logs/runtime_measure_torch.csv`의 forecast_torch(Python 호출: 변환·호출·역변환 포함), forecast_lstmnat(MATLAB 재구현). 실측 p95가 `config/latency_measured.json`에 들어가 예측 준비 지연(d_fc)으로 쓰입니다.

## 폐루프 연결 시험 (El Centro 1회, 성능 판정 아님)
`results/comparison_summary_T_connect.csv`, `logs/runtime_T_connect.csv`
