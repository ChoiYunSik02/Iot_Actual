# 참고문헌 — 최근 4년 (2022~2026)

## ★ 논문을 고르는 규칙 — 학교에서 받을 수 있는 것 우선

국립군산대 도서관 기준. 새 논문을 제시할 때는 **접근 경로를 반드시 함께 표기**합니다.

| 표기 | 대상 | 비고 |
|---|---|---|
| `ScienceDirect ✅` | Elsevier 전 저널 (1995~) | 가장 넓게 커버됨 — **1순위** |
| `IEEE ✅` | 전기·전자·컴퓨터 (1988~) | |
| `오픈액세스 ✅` | PLOS, MDPI, SpringerOpen/BMC(10.1186), arXiv, KCI·DBpia | 누구나 |
| `Wiley ⚠️` | KERIS 제공 (1997~2024) | **2년 엠바고** — 최신은 불가 |
| `무료복사 필요 ❌` | **Springer (10.1007)** | 구독 없음. 도서관 44번 「외국학술지지원센터 무료복사」, 며칠 소요 |

구독 밖 논문만 제시하지 말고, 같은 주제의 **Elsevier·IEEE·오픈액세스 대체 논문**을 함께 찾습니다.
교외접속 시 여러 DB가 RISS 개인 로그인을 요구합니다.

지도교수가 오래된 문헌을 선호하지 않으므로 **2022년 이후 논문만** 인용합니다.
1997·2000·2012년 고전(Agrawal 안정성, 최적 파라미터, 국내 액체댐퍼)은 의도적으로 제외했습니다.

## 기초 · 검증

**An experimental study of tuned liquid column damper controlled multi-degree of
freedom structure subject to harmonic and seismic excitations**
Mati Ullah Shah, Muhammad Usman · PLOS ONE, 2022 · **Open Access**
DOI: 10.1371/journal.pone.0269910

- 4층 강프레임 + 옥상 TLCD, 진동대 실험
- 파라미터: 질량비 5%, 튜닝비 0.98, 길이비 0.8 ← **본 연구 초기값의 출처**
- 입력: 조화가진 5종 + El Centro 1940
- 결과: 공진 시 RMS 가속도 67~85% 저감, **지진 시 23~35% 저감**
- → 우리 모델의 **검증 기준선**. 무료 공개라 전문 즉시 확보 가능.

## 단주기 구조 (3층 모델과 직결)

**Optimal design of short-period structures equipped with sliding tuned liquid
column damper and numerical and experimental control performance evaluation**
C. Masnata, C. Adam, A. Pirrotta · Acta Mechanica, 2024
DOI: 10.1007/s00707-023-03832-8

- U자관을 레일 위에서 슬라이딩시켜 단주기 구조물에 튜닝
- 팔레르모 대학 실험실 검증
- → **저층 건물 TLCD 튜닝 난점**을 정면으로 다룬 논문. 리스크 대응의 근거.

## 저 · 중층 적용 (최신)

**Seismic control of mid-rise building using sealed tuned liquid column damper
and compliant liquid column damper: a comparative study**
Journal of Infrastructure Preservation and Resilience, 2026
DOI: 10.1186/s43065-026-00184-0

- 6층 RC 건물, 6개 실측 지진파로 수치 시뮬레이션
- 핵심 지적: *"주기가 짧은 저·중층 건물에서는 기존 TLCD 설계가 어렵다"*
- → 발행 연도가 가장 최신. "최신 문헌 반영" 근거로 가장 강력.

## 형상 · 파라미터

**U-shaped and V-shaped tuned liquid column dampers in vibration reduction of
earthquake-induced buildings: A comparative study** · Structures, 2024

**Efficient estimation of tuned liquid column damper inerter (TLCDI) parameters
for seismic control of base-isolated structures**
Masnata et al. · Computer-Aided Civil and Infrastructure Engineering, 2023
DOI: 10.1111/mice.12929

**Efficiency evaluation of optimal TLCD and TMD for the seismic response
reduction of buildings considering soil-structure interaction effect**
Meccanica, 2025 · DOI: 10.1007/s11012-025-01981-9
→ TLCD vs TMD 직접 비교. **1단계 실험 설계**에 참고.

## 준능동 제어 (연구축 ②)

**Rotating semi-active tuned liquid column damper for bi-directional eccentric
structural seismic response control** · Journal of Building Engineering, 2025

**Semi-active tuned liquid column damper applied for offshore wind turbines
random vibration control using groundhook control strategies**
Ocean Engineering, 2025

> 알려진 수치: **준능동 TLCD는 고정 오리피스 대비 성능 15~25% 향상**.
> 우리 결과가 이 범위에 들면 신뢰도가 확보됩니다.
>
> 또한 **S-TLCD는 건물 고유진동수가 변해도 성능이 유지된다**는 보고가 있습니다.
> → 디튜닝 강건성(3단계)의 근거.

## 제어 지연

**Time-delay compensation control and stability analysis of vehicle semi-active
suspension systems** · Mechanical Systems and Signal Processing, 2025
→ 차량 사례지만 준능동 지연·안정성 방법론 참고용.

**An Elman neural network approach in active control for building vibration
under earthquake excitation**
Frontiers of Structural and Civil Engineering, 2025
DOI: 10.1007/s11709-025-1156-9

> ⚠️ **주의**: 문헌상 *"준능동 시스템은 본질적으로 안정하므로 지연에 의한
> 불안정은 발생하기 어렵다"*는 견해가 있습니다. 밸브 기반 준능동 TLCD에서는
> 발산이 안 나올 수 있으니, **성능 저하율**을 주 지표로 잡으세요.

## 입력 지진파 원자료 (연도 무관 — 1차 데이터)

- 기상청 「포항지진 분석 보고서」 — https://www.weather.go.kr/w/download/earthquake_pohang.pdf
- 「9.12 경주지진 및 11.15 포항지진의 구조손상 포텐셜 비교연구」 — 한국지진공학회
- El Centro 1940 — PEER NGA-West2 (무료, 가입 필요)

## 접근 방법

- **무료로 바로**: PLOS ONE 2022, 기상청 보고서, 경주·포항 비교연구(KISTI ScienceON)
- **학교 프록시 필요**: ScienceDirect, Springer, ASCE, Wiley
- 안 열리면 KISTI ScienceON / DBpia에서 검색하거나 저자에게 메일 요청

## 미확인 사항

국내 학회(한국소음진동공학회·한국지진공학회)의 **2022년 이후 TLCD 논문**은
검색으로 확인하지 못했습니다. DBpia·KCI에서 학교 계정으로 직접 검색하면
나올 가능성이 있으니, 찾으면 이 파일에 추가하세요.
