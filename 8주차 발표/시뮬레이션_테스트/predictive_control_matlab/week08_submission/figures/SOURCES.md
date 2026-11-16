# 그림 ↔ 근거 CSV

모든 그림은 `make_figures.py`로 노트북 MATLAB 실행 결과 CSV에서 생성했습니다.

| 그림 | 근거 |
|---|---|
| `fig1_timeline.png` | `F8_runs.csv (d_cmd)` |
| `fig2_forecast_examples.png` | `F8_forecast_examples.csv` |
| `fig2b_forecast_error.png` | `../results/forecast_metrics_pilot8_seed840{1,2,3}.csv`, `F8_forecast_remaining_error.csv` |
| `fig3_response_ElCentro_1940.png` | `F8_series_ElCentro_1940.csv` |
| `fig4_actuator_ElCentro_1940.png` | `F8_series_ElCentro_1940.csv`, `F8_commands_ElCentro_1940.csv` |
| `fig3_response_PEER14.png` | `F8_series_PEER14.csv` |
| `fig4_actuator_PEER14.png` | `F8_series_PEER14.csv`, `F8_commands_PEER14.csv` |
| `fig3_response_Pohang_2017_BUS2.png` | `F8_series_Pohang_2017_BUS2.csv` |
| `fig4_actuator_Pohang_2017_BUS2.png` | `F8_series_Pohang_2017_BUS2.csv`, `F8_commands_Pohang_2017_BUS2.csv` |
| `fig3c_torsion_all.png` | `F8_series_ElCentro_1940.csv`, `F8_series_PEER14.csv`, `F8_series_Pohang_2017_BUS2.csv` |
| `fig5_reduction_S_main.png` | `F8_event_metrics.csv` |
| `fig5_reduction_C_ref.png` | `F8_event_metrics.csv` |
| `fig7_reduction_all.png` | `F8_event_metrics_all.csv` |
| `fig6_training_latency.png` | `../models/torch_pilot8_seed840{1,2,3}.json`, `F8_runs.csv`, `../logs/runtime_measure_pilot8_seed8401.csv` |
