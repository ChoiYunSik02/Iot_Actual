# 8주차 v2: 펌프·회전판·밸브 공동 선택 비교 (탐색적, 개발 평가)

- 실행: MATLAB 26.1.0.3346908 (R2026a) Update 5, 커밋 `cd932e8565ea3df19bcf65ac61fe1984ddac972f`, 코드 digest `53d82e1bfbce45aa`, 설정 `c4569a5ef9164ed5`
- 사건: ImperialValley1979, Northridge1994, Kobe1995, ChiChi1999, ElCentro1940, Pohang2017, Gyeongju2016 — 모두 이전 개발에 쓰인 기록이므로 **개발 평가**
- 파형 AI `C:\Users\cys\Desktop\iot-actuator-week08\predictive_control_matlab\models\torch_pilot8_seed8401`, 공동 후보 점수망 `C:\Users\cys\Desktop\iot-actuator-week08\predictive_control_matlab\models\joint_scorer_seed8401` (합성 teacher 80/20 기록, 실제 기록 미사용)
- 공통 고정 시간축: 느린 결정 0.27 s, 빠른 결정 0.22 s (J-AI 지속 부하 p99), 센서·통신 0, 예측 준비 1스텝, R 1스텝. 이상화 알고리즘 비교이며 전체 후보 방식의 실시간 가능성은 아래 계산시간으로 따로 판정
- 이상적 상태정보 조건(플랜트 상태 사본). 그림자 R 제한은 예측에 의존하며 실제 무악화를 보장하지 않음

점수망 검증(합성 val, 느린 결정, 실제 미래 teacher): top 3 적중 0.20 (무작위 0.08), 검사 집합 최선 포함 0.64, regret 0.0129 (무작위 0.0108), fallback 0.61

## actual (actual)

사건 순서: ChiChi1999, ElCentro1940, Gyeongju2016, ImperialValley1979, Kobe1995, Northridge1994, Pohang2017. 평균 단위: 6지표 → 기록 → 사건 내 → 사건 동일 가중.

| 방식 | S % | R 대비 %p | 사건별 | 위반 사건/기록 | 최악 비틀림 | 느린: 유지/R/tuple | AI tuple 적용 | 빠른: 후보/R | no_feasible | 늦음 | 밸브 전환 | κ 이동 | 선택 p99 느린/빠른 s | 실시간 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R | 12.89 | +0.00 | +0.00 +0.00 +0.00 +0.00 +0.00 +0.00 +0.00 | 0/0 | +0.00 | 0/100/0 % | 0 | 0/100 % | 0 % | NaN % | 42.1 | 18.01 | NaN/NaN | — |
| J-AI | 16.53 | +3.64 | +6.87 +4.65 +7.03 +5.37 -0.52 +1.95 +0.15 | 2/3 | -1.64 | 35/48/17 % | 49 | 49/51 % | 32 % | 2 % | 32.6 | 15.28 | 0.28/0.23 | 가능 |

실행: actual(2026-10-29 23:54:22~2026-10-29 23:58:00) 
