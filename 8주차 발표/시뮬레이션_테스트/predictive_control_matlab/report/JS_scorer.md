# 공동 후보 점수망 학습 (8주차 v2, seed 8401)

- 실행: MATLAB 26.1.0.3346908 (R2026a) Update 5, 커밋 `f7fb88d68dade686081664044c927bb5d40e3cb4`, digest `53d82e1bfbce45aa`. teacher `data/joint_teacher.csv` (sha16 `1f8be9ebecf27156`)
- 망 98 → 128 → 64 → 1, Huber, Adam 0.001, batch 128, 최대 50 epoch, patience 5. 종료 epoch 3 (최저 검증 손실 0.00549), 11 s
- 목표 J_true/J_true(R) − 1 (실제 미래로 모의한 비인과 teacher). 제약 판정은 망이 아니라 물리 모델이 한다.
- 행 train 14314 / val 3725, 상태 train 624 / val 160. 자료 보강(정책 rollout 1회): 미실행
- Python 대 MATLAB 추론 최대 차 1.4e-16

| 분할 | top 3 적중 | 검사 집합(top3+유지+R) 최선 포함 | regret (J_R 대비) | fallback |
|---|---|---|---|---|
| train | 0.314 | 0.747 | 0.0024 | 0.615 |
| train (무작위 3개) | 0.077 | 0.637 | 0.0048 | 0.588 |
| val | 0.204 | 0.637 | 0.0129 | 0.613 |
| val (무작위 3개) | 0.079 | 0.575 | 0.0108 | 0.509 |

80/20 합성 기록 규모의 마감용 탐색 실험이며 일반화 검증이 아니다.
