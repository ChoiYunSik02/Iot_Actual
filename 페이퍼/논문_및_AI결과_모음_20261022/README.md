# 논문 초안 + AI 학습·테스트 결과 모음 (2026-10-22)

| 폴더 | 내용 |
|---|---|
| 1_논문초안 | 논문_초안_v2.docx / .md (영어, Smart Structures and Systems 투고용 초안) |
| 2_원고_섹션별 | 섹션별 원고 (0 초록, 1 서론, 2 모델, 3 검증, 4 이득 분석, 5 AI 예측, 6 결론, 7 그림 캡션, 8 참고문헌) |
| 3_그림 | 논문 그림 6장 (G1→Fig.1, G2→Fig.2, G4→Fig.3, G6→Fig.4, G8→Fig.5, G7→Fig.6) |
| 4_AI학습_테스트결과 | ai_eval_v2_cos2.json (AI 9조건), exp_switch*(시변 스위칭), paper_tests(강건성), check_peer_c30*(Table 3), freq_vs_best(유입 진동수 검증), table2.md |
| 5_실험코드 | 위 결과를 만든 코드와 README_v2 (실행 명령 포함) |

핵심 결과 (공칭 건물, T_obs 3 s, 6지표 평균 저감률): 수동 13.36 / 원 RS 14.04 / 고정 15.81 / AI 사전 15.58 / AI 온라인 15.64 / Oracle 17.60 (%).
AI는 원 RS보다 +1.5%p이나 고정 설정과는 같은 수준 (지진 7개 기준 차이 < 오차).
초안 재생성: 상위 폴더에서 `python build_manuscript.py`
