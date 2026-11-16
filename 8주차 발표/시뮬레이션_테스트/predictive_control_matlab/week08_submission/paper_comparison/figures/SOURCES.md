# v3 그림 ↔ 원자료

새 계산 없이 이미 실행된 CSV에서만 만들었다. R 재현(지연 0)의 출처: MATLAB

| 그림 | 자료 |
|---|---|
| `fig_v3_1_reproduction.png` | paper_tables_4_6.csv, reproduction_metrics.csv (현재 R = JC 고정 시간축, ../results/control_metrics_record_JC_fixed_all.csv) |
| `fig_v3_2_matched_R_AI.png` | matched_R_AI_metrics.csv (J-AI, 고정 시간축) |
| `fig_v3_3_response_PEER11.png` | ../results/JC_series_PEER11_all.csv (U, R, J-AI 열) |
| `fig_v3_3_response_PEER14.png` | ../results/JC_series_PEER14_all.csv (U, R, J-AI 열) |
| `fig_v3_4_actuators.png` | ../results/JC_series_PEER11_all.csv, JC_series_PEER14_all.csv (R, J-AI 열: pump_f_dev_hz, rotation_rad, valve_kappa) |
| `fig_v3_5_delay.png` | matched_R_AI_metrics.csv, matched_R_AI_summary.csv (J-AI, 고정 시간축·실측 1차·실측 2차) |
