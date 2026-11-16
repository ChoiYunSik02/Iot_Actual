# 노트북 MATLAB 검증 체크리스트 (A~D, E·F 보류)

클라우드에서는 MATLAB/Simulink를 실행하지 못했습니다. 아래 항목은 **노트북에서 실행해야만 완료로 표시**할 수 있습니다.

## 0. 받기
```bash
git fetch origin
git checkout claude/focused-gauss-ubza04
git pull origin claude/focused-gauss-ubza04
```
- 실행 브랜치·커밋은 매 실행마다 `report/progress_laptop.md`, `results/gate_*.json`, `logs/provenance_*.json`, `logs/environment.json`에 자동으로 기록됩니다.
- git이 없거나 zip으로 받으면 `.git/HEAD`를 읽고, 그것도 없으면 `unknown`과 코드 digest만 남습니다.
- 작업트리에 커밋하지 않은 변경이 있으면 `dirty = true`로 기록됩니다. 가능하면 변경 없는 상태에서 실행하세요.

## 실행
```matlab
cd predictive_control_matlab
run_week08_laptop        % A → B → SL → C → D. 한 단계라도 실패하면 거기서 멈춤
```
- D는 `gate('require', {'A','B','SL','C'})`로 다음을 확인합니다.
  - 네 관문이 모두 **MATLAB에서 통과**했는지
  - 그 뒤 `src/`·`tests/`·`config/scales.json`이 바뀌지 않았는지(코드 digest)
  - 설정이 바뀌었다면 `config/CHANGELOG.md`에 기록됐는지
- 하나라도 어긋나면 D를 시작하지 않습니다.

## A. 환경 → `results/gate_A.json`
- [ ] `version`, `ver`, 라이선스, GPU, 메모리, 코어 수, 실행 브랜치·커밋 → `logs/environment.json`
- [ ] `config/scales.json`(Octave에서 생성)을 MATLAB으로 다시 계산해 상대차 ≤ 1e-9

## B. 기준 재현 → `results/gate_B.json`
- [ ] `results/stage_B_check.csv`의 overall_pass = 1 (Octave 예비: `rstlcd_sim.m` 대비 6.7e-14, Python 대비 3.0e-10)

## SL. Simulink 대 MATLAB 스텝 엔진 → `results/gate_SL.json`
- [ ] `models/rs_tlcd_predictive_control.slx` 생성
- [ ] `results/simulink_check.csv`의 overall_pass = 1
  - 대상: U·R·FIX·SIMPLE-zero × 지연 0·지연 있음
  - 판정: 응답 ≤ 1e-12, 장치 상태 일치, 결정·적용 기록 일치
  - 클라우드에서 한 번도 실행하지 못한 코드입니다. 빌드나 실행 오류가 나면 메시지 전체를 보내 주세요.
  - Simulink가 없으면 SL 관문이 실패하고 D로 넘어가지 않습니다(의도한 동작).

## C. 지연·큐·인과성·실제 계산시간 → `results/gate_C.json`
- [ ] `results/stage_C_check.csv`의 overall_pass = 1 (Octave 예비 31/31)
  - T8a~d: 계산이 끝나기 전 적용 금지, 늦은 지령 → R 또는 보류, 예측 준비 = 시작 + 실측

## D. 실측 계산시간 + 개발 진단
- [ ] `measure_runtime` → `config/latency_measured.json`, `logs/runtime_measure.csv`
  - 선택 계산(R, C1, C2)과 예측 갱신(zero, persistence, preview, 학습 전 같은 구조 LSTM)을 따로 잽니다.
- [ ] `diagnose_D` → `report/D_diagnosis.md` (표 5개 자동 작성) + `results/D_*.csv` + `results/fig_D_pohang_torsion.png`
  1. SIMPLE-persistence 대 PREVIEW-C1 분해: `results/D_decomposition.csv`
  2. 예측 준비→적용 경과, 남은 예측 구간, 늦음: `results/D_timing.csv`, `logs/command_timeline_D_main.csv`
  3. 포항 비틀림 악화 구간·지령: `results/D_pohang_torsion_intervals.csv`, `D_pohang_series.csv`, 그림
  4. 한 요소씩 진단(Δf, Δθ, H): `results/D_ofat.csv`
  5. AI 학습 판단 기준 G1~G4와 예상 비용: `report/D_diagnosis.md` 5절, `results/training_cost_estimate.csv`
- 예상 시간: C1형 폐루프 약 80회(D_main 9 + 진단 기록 + 지연 0 비교 9 + 한 요소 변형 54). 1회 시간은 D 초반 실측으로 정해집니다.

## T. PyTorch smoke 학습·추론 연결 (Deep Learning Toolbox 대체, 정식 pilot 아님)
- 준비(한 번): 노트북 Python에 `pip install -r python/requirements.txt` (torch, numpy, h5py, scipy)
- MATLAB에서 Python 지정(필요 시): `pyenv('Version', '<python.exe 경로>', 'ExecutionMode', 'OutOfProcess')`
- [ ] `run_week08_laptop({'T'})` → `report/T_torch_smoke.md`, `logs/torch_smoke_train.log`, `results/forecast_metrics_smoke_torch.csv`, `logs/runtime_measure_torch.csv`
  - 자료는 MATLAB `build_forecast_dataset('smoke')` 그대로(입력·정답·분할 유지), 최대 10 epoch
  - Python 호출(변환·호출·역변환 포함) 시간 p95가 `config/latency_measured.json`의 `forecast_torch`로 들어가 예측 준비 지연에 반영됩니다.

## D2. 후보 집합·R 후보 대 R·구간 끝 잔여 진동 + 통합 표
- [ ] `run_week08_laptop({'D2'})` → `report/D2_summary.md`(통합 표), `results/D2_candidates.csv`
  - 후보 집합 ±15°(현행)/±30°/±45°/확장 {0,±15,±30,±45}° — ±30° 이상은 진단 후보, 채택 아님. 집합마다 선택 예산을 다시 잽니다.
  - R-lag(결정 앞당김만 C1과 같게) 실행, R 후보 지령 대 R 실행 지령·상태 분기
- 예상 시간: C1형 폐루프 약 40회 + R 15회 (D 실측 1회 평균 17.8 s 기준 약 15~25분, 확장 집합은 후보가 많아 더 김)

## RP. 재현성 진단 (현행 ±15°, AI 학습·후보 채택 보류)
- [ ] `run_week08_laptop({'RP'})` → `report/RP_summary.md`, `results/RP_runs.csv`, `results/RP_event_metrics.csv`, `results/RP_fixed_compare.csv`, `results/RP_dcmd_timeline.csv`
  1. 완전 고정 2회(nominal, 센서·통신 0, 예측 준비 1스텝, R 1스텝, C1 d_cmd 51): 지령·응답 비트 단위 비교. 다르면 여기서 멈추고 원인 기록
  2. d_cmd 50 대 51 (그 밖의 조건 동일): 결정·마지막 관측·예측 기준·준비·적용 시각 기록
  3. 실측 지연 5회: 시작할 때 `config/latency_measured.json`을 한 번 읽어 고정(`results/RP_latency_frozen.json`), 재측정 안 함
- 실행 중에는 다른 무거운 프로그램을 끄고, 노트북 전원을 연결해 두세요(실측 지연 5회의 계산시간 조건). 실행 순서·시각은 보고서에 자동 기록됩니다.
- 예상 시간: C1형 폐루프 약 72회 (1회 20~50 s) → 약 40~60분

## P → F8. 8주차 소규모 AI 학습과 최종 폐루프 비교 (사전 지정 `report/prereg_week8_final.md`)
- 준비: MATLAB 시작 직후 `pyenv('Version', '<python.exe 경로>', 'ExecutionMode', 'OutOfProcess')`
- [ ] `run_week08_laptop({'A','B','SL','C'})` (설정·코드가 바뀌어 관문 재통과 필요)
- [ ] `run_week08_laptop({'P','F8'})`
  - P: 학습 자료 생성 → PyTorch 1시드 학습(최대 20 epoch) → 출력 일치 → 예측 진단 → 예측 계산시간. `report/P_ai_pilot.md`
  - F8: 지속 부하 예산 측정 → 개선안(±45°) 주 조건·d_cmd ±1·실측 1회 + 기존(±15°) → `report/F8_summary.md`, `results/F8_runs.csv`
- 예상 시간: P 약 30~60분(학습 장치에 따라), F8 약 2~3시간. 전원 연결, 다른 무거운 프로그램 종료.

## 끝나면 올릴 것
`report/`, `results/`(`.mat` 제외), `logs/`, `config/latency_measured.json`, `models/rs_tlcd_predictive_control.slx`를 커밋하고 푸시해 주세요. 그 결과로 발표 자료를 만들 때 완료된 MATLAB 결과와 미실행 AI 계획을 나눠 표시합니다.

## E·F (보류)
- 실행하려면 `run_week08_laptop({'E'})`처럼 명시합니다. 이때도 A·B·SL·C 관문을 다시 확인합니다.
- 설정을 바꿨다면 `config/CHANGELOG.md` 기록 → A~D 재실행 → F 전에 `config/frozen/`으로 고정합니다.
