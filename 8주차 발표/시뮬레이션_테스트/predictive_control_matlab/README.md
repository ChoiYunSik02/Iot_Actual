# predictive_control_matlab — 30층 RS-TLCD 반복 AI 파형 예측 · 지연 고려 제어

계획서 `../Week08_ClaudeCode_MATLAB_Simulink_AI예측제어_실행계획.md`를 구현한 MATLAB/Simulink 작업 폴더입니다.
기준 엔진 `../code/matlab/rstlcd_sim.m`과 기존 7·8주차 결과는 수정하지 않았습니다.

> **상태 (2026-10-28):** 클라우드에는 MATLAB/Simulink가 없습니다. 코드 작성, Octave 8.4 예비 점검(B·C 단계, D 단계 일부), 노트북 실행 스크립트 준비까지만 했습니다.
> **MATLAB 공식 판정, Simulink 대조, LSTM 학습, AI 제어 결과는 아직 없습니다.** 진행 상황은 `report/progress.md`에 있습니다.

## 노트북에서 실행
```matlab
cd predictive_control_matlab
run_week08_laptop                 % A 환경 → B 기준 재현 → SL Simulink 대조 → C 지연·인과성·실제 계산시간 → D 진단
run_week08_laptop({'E'})          % (보류) smoke 학습
run_week08_laptop({'F'})          % (보류) pilot 1,000원본 × 3시드
```
- 단계가 실패하면 거기서 멈춥니다. 기록은 `report/progress_laptop.md`에 남습니다.
- 관문: A·B·SL·C 결과를 `results/gate_*.json`(실행 브랜치·커밋·코드 digest)에 남깁니다. D 이후는 넷 다 MATLAB에서 통과했고 그 뒤 코드가 바뀌지 않았을 때만 시작합니다(`src/gate.m`).
- D 진단 결과는 `report/D_diagnosis.md`에 자동으로 정리됩니다(`scripts/diagnose_D.m`).
- 결과 파일에는 실행 환경(`MATLAB …` / `Octave … (예비)`)이 함께 적힙니다. Octave 예비 결과는 파일 이름에 `_octave`가 붙습니다.
- 확인할 항목은 `report/laptop_checklist.md`에 정리했습니다.

## 구조
| 경로 | 내용 |
|---|---|
| `config/experiment.json` | 시간축·후보·학습·평가 설정 (계획서 5·8·9·12절 제안값) |
| `config/scales.json` | 목적함수 스케일 sx·sy·st (예측기 학습 사건의 R 응답 RMS, 동결) |
| `config/latency_measured.json` | 노트북 실측 계산 지연 (D 단계에서 생성) |
| `data/records/dt0.01`, `dt0.005` | 개발 기록 11개(사건 7개) CSV, `scripts/export_records.py`(7주차 전처리 그대로) |
| `data/record_manifest.csv` | 사건·관측소·성분·출처·필터링·분할 |
| `data/reference/validation_ref.mat` | Python 엔진 기준값 (week08_actuator_ai_results zip, 수정 없음) |
| `src/` | 한 스텝 엔진과 단계 함수 (아래 표) |
| `src/sl/` | Simulink MATLAB System 블록 (`PCPlant`, `PCStage`) |
| `scripts/` | 환경 점검, 자료·학습·평가·벤치마크, Simulink 빌드·실행 |
| `tests/` | B·C 단계 시험, LSTM 배열 단위시험, Simulink 대 엔진 대조 |
| `run_week08_laptop.m` | 노트북 단계 실행기 |
| `preregistration.md` | 사전 등록 (F 단계 전에 `config/frozen/`으로 동결) |

### 스텝 i 처리 순서 (MATLAB 엔진과 Simulink 모델 공통)
`Plant30Story 출력 x_i` → `SensorAndLatency` → `ObservationBuffer` → `Forecaster` → `StateEstimator` → `CommandSelector` → `CommandQueue` → `Actuators` → `Plant30Story 갱신 (i → i+1)`

| 서브시스템 | 함수 | 핵심 규칙 |
|---|---|---|
| GroundMotion | `run_closed_loop` 입력 | 전체 미래는 이곳과 PREVIEW 예측기만 접근 |
| Plant30Story | `plant_init`, `plant_step` | `rstlcd_sim.m`과 같은 식(92 자유도, Newmark), 직접 통과 없음 |
| SensorAndLatency | `sensor_step`, `plant_measure` | 정수 스텝 대기열, 측정 시각(stamp) 보존 |
| ObservationBuffer | `obsbuffer_step`, `make_window` | 도착한 100 Hz 샘플만, 5 s 창, 트리거 이후 mask 1 |
| Forecaster | `forecaster_step`, `forecast_simple`, `forecast_lstm` | 0.2 s 갱신, 작업자 1개, 기준시각 = t_obs, 계산 지연 뒤 사용 |
| StateEstimator | `state_estimator_step` | 1차: 이상적 상태정보 (센서 관측기 미구현) |
| CommandSelector | `selector_step`, `predict_response`, `reference_R_step` | 격자 g − d_cmd에 결정, C1/C2 후보, 비틀림 제한, R 복귀 |
| CommandQueue | `command_queue_step` | 적용 스텝에만 내보냄, 늦은 지령 만료 |
| Actuators | `actuator_step` | 펌프 2.6 s 램프, 회전 30°/s, 범위 제한 |
| Evaluator | `response_metrics`, `compute_scores` | 사후 평가 전용 (제어기로 되먹임 없음) |

## 클라우드(Octave) 예비 점검 다시 돌리기
```bash
cd predictive_control_matlab
octave-cli -q --eval "addpath('tests'); test_stage_B(); test_stage_C();"
```
