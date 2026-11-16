# 실행 로그 (v3)

| 시각(KST) | 작업 | 환경 | 결과 위치 | 비고 |
|---|---|---|---|---|
| 2026-10-29 21:40~22:19 | JB·JT·JS·JC (개발 3사건 + J-AI 실측 지연) | 노트북 MATLAB R2026a, 커밋 `f7fb88d`, digest `53d82e1bfbce45aa`, 설정 `c4569a5ef9164ed5` | `../results/JC_*`, `../../results/control_metrics_record_JC_fixed.csv`, `…_JC_actual.csv`, `report/JC_summary.md` | v2 결과, 변경 없이 사용 |
| 2026-10-29 22:23~23:00 | JCX (기존 11개 기록, 고정 시간축) | 노트북 MATLAB, 커밋 `265be4e`, 같은 digest·설정 | `../results/JC_*_all.csv`, `../../results/control_metrics_record_JC_fixed_all.csv`, `report/JC_summary_all.md` | 결과 푸시 커밋 `0c0dbc8` |
| v3 | 원문 표 4-6 전사·표 7 대조 | Python (pdftotext) | `paper_tables_4_6.csv` | `extract_paper_tables.py` |
| v3 | 지진 자료 manifest | Python | `record_manifest.csv` | 원본 AT2 hash, 헤더 대조 |
| v3 | 원문 대응표 | 문서 대조 | `condition_mapping.csv/.md` | 44항목 |
| v3 | 원문 재현 조건 R (지연 0, dt 0.01) | Octave 8.4 예비 | `PR_records_octave.csv` | 이후 MATLAB 결과와 소수 9자리까지 같음을 확인(참고만) |
| v3 | 비교표·그림 생성 | Python | `reproduction_*.csv`, `matched_R_AI_*.csv`, `figures/` | 새 폐루프 계산 없음, 기존 CSV에서만 |
| 2026-10-29 23:53 | `PR` (원문 재현 조건 R, dt 0.01·0.005, 42 s) | 노트북 MATLAB R2026a, 커밋 `cd932e8`, digest `53d82e1bfbce45aa` | `PR_records.csv`, `checkpoint_hashes.json` | 푸시 커밋 `3db2cec` |
| 2026-10-29 23:54 | `JCA` (11개 기록 R·J-AI 실측 지연, 222 s) | 같음 | `../../results/control_metrics_record_JC_actual_all_actualall.csv`, `../results/JC_*_all_actualall.csv`, `report/JC_summary_all_actualall.md` | 푸시 커밋 `3db2cec` |
| v3 | 표·그림을 MATLAB 결과로 다시 생성 | Python | `reproduction_*.csv`, `matched_R_AI_*.csv`, `figures/` | 실측 지연 1차·2차를 구분 |

설정 값(예산 0.27/0.22 s, 모델, 점수망)은 v2 실행 그대로이며 이번 v3에서 바꾸지 않았다. 새 AI 구조 탐색·추가 학습은 하지 않았다.
