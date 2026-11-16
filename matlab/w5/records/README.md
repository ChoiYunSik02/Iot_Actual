# 실관측 지진 기록 (5주차)

| 파일 | 지진 | 관측소 | 진앙거리 | 원 PGA | 비고 |
|---|---|---|---|---|---|
| `pohang_BUS2_BHE.txt` | 포항 2017-11-15 ML5.4 | KS.BUS2 부산, 동서 | 98.2 km | 0.0020 g | 광대역 속도계 → 가속도 환산 |
| `gyeongju_BUS2_BHN.txt` | 경주 2016-09-12 ML5.8 | KS.BUS2 부산, 남북 | 58.1 km | 0.0099 g | 동서 성분은 디지타이저 포화(clip) 의심으로 제외 |
| `elcentro_NS.txt` | Imperial Valley 1940 M6.9 | El Centro, 남북 | — | 0.349 g | vibrationdata.com 공개본, 단위 g, dt 0.02 s |

- 한국 기록 출처: EarthScope(구 IRIS) FDSN, 기상청 KS 네트워크. `fetch_korea_records.py`(ObsPy)로 재현.
  - 응답 스테이지 정보가 없어 **감도(6.29e8 counts/(m/s))로 속도 환산 → 미분 → 0.1–8 Hz 대역통과**.
  - 시간축 0 = 진원시. 열: t [s], 가속도 [m/s²].
- **한계:** 부산 관측소는 진앙에서 58~98 km 떨어져 있어 근거리 강진동과 주파수 특성이 다름.
  실험에서는 목표 PGA로 스케일해 **파형 형태만** 사용. 근거리 기록(기상청 지진화산 자료실, 가속도계)으로 교체 권장.
- El Centro 원본 PEER RSN 6과 같은 기록인지(보정 버전 차이)는 확인 필요.

## X·Y 2축 실험용 (2026-10-04 추가)

| 기록 | X 성분 | Y 성분 | 관측소 · 거리 | 원 PGA (X / Y) |
|---|---|---|---|---|
| 포항 2017 | `pohang_BUS2_BHE.txt` | `pohang_BUS2_BHN.txt` | KS.BUS2 부산 · 98 km | 0.0020 / 0.0014 g |
| 경주 2016 | `gyeongju_CHJ2_BHE.txt` | `gyeongju_CHJ2_BHN.txt` | KS.CHJ2 충주 · 164 km | 0.0032 / 0.0028 g |
| El Centro 1940 | `elcentro_NS.txt` | `elcentro_EW.txt` | — | 0.349 / 0.214 g |

- 경주는 부산 동서 성분이 디지타이저 포화(9.24e6 > 2²³ counts)라 **충주 관측소로 대체** (두 성분 모두 포화 없음 확인)
- 내려받기: `fetch_korea_records_2axis.py` (포화 검사 포함)
- 두 성분에 같은 배율을 곱해 **큰 성분의 PGA = 목표 PGA**
- 한국 기록은 **P파 도착 5 s 전부터** 60 s를 사용 (충주는 S파가 진원 후 47 s에 도착하므로)
- 1축 실험은 기존 파일(부산 경주 남북)을 그대로 사용 — 1축 결과는 바뀌지 않음
