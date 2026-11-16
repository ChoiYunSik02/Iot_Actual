# 입력 지진 — 원문(Fu et al. 2025) 표 2의 15쌍

PEER NGA-West2는 **로그인(무료 회원가입)** 이 필요해서 자동으로 받을 수 없습니다. 직접 받아 `페이퍼/입력/PEER/`에 넣어 주세요.
`코드/records.py`가 **파일 이름 안의 사건 코드 + 성분 코드**(예: `IMPVALL` + `E11140`)로 자동으로 찾으므로, 폴더 구조나 RSN 번호는 상관없습니다.

## 받는 방법

1. https://ngawest2.berkeley.edu 접속 → 회원가입 · 로그인
2. **Spectral Matching** 아무 스펙트럼으로 시작 (기본값 그대로 Submit)
3. 검색 창 **RSN** 칸에 아래 번호를 쉼표로 넣기 → Search
   `170,173,174,178,180,182,183,184,185,158,159,161,1050,1106,1182`
4. 결과에서 **관측소 이름이 아래 표와 같은지 확인** → 전체 선택 → **Download Selected Records**
5. 받은 zip을 풀어 `.AT2` 파일들을 `페이퍼/입력/PEER/`에 넣기 (수직 성분 `UP` · `DWN`은 없어도 됨)

⚠️ RSN 번호는 기억에 의존한 값입니다. **관측소 이름과 성분 코드로 확인**해 주세요. 틀리면 검색 화면의 Event Name · Station Name으로 찾으면 됩니다.

| 번호 | 지진 | 관측소 | RSN (확인 필요) | X 성분 | Y 성분 |
|---|---|---|---|---|---|
| 1 | Imperial Valley-06 1979 | El Centro Array #11 | 174 | IMPVALL-E11140 | IMPVALL-E11230 |
| 2 | Imperial Valley-06 1979 | Aeropuerto Mexicali | 158 | IMPVALL-AEP045 | IMPVALL-AEP315 |
| 3 | Imperial Valley-06 1979 | El Centro Differential Array | 184 | IMPVALL-EDA270 | IMPVALL-EDA360 |
| 4 | Imperial Valley-06 1979 | Brawley Airport | 161 | IMPVALL-BRA225 | IMPVALL-BRA315 |
| 5 | Imperial Valley-06 1979 | EC County Center FF | 170 | IMPVALL-ECC002 | IMPVALL-ECC092 |
| 6 | Imperial Valley-06 1979 | El Centro Array #10 | 173 | IMPVALL-E10050 | IMPVALL-E10320 |
| 7 | Imperial Valley-06 1979 | Agrarias | 159 | IMPVALL-AGR003 | IMPVALL-AGR273 |
| 8 | Imperial Valley-06 1979 | El Centro Array #5 | 180 | IMPVALL-E05140 | IMPVALL-E05230 |
| 9 | Imperial Valley-06 1979 | El Centro Array #7 | 182 | IMPVALL-E07140 | IMPVALL-E07230 |
| 10 | Imperial Valley-06 1979 | El Centro Array #8 | 183 | IMPVALL-E08140 | IMPVALL-E08230 |
| 11 | Imperial Valley-06 1979 | El Centro Array #3 | 178 | IMPVALL-E03140 | IMPVALL-E03230 |
| 12 | Imperial Valley-06 1979 | Holtville Post Office | 185 | IMPVALL-HVP225 | IMPVALL-HVP315 |
| 13 | Northridge-01 1994 | Pacoima Dam (downstr) | 1050 | NORTHR-PAC175 | NORTHR-PAC265 |
| 14 | Kobe 1995 | KJMA | 1106 | KOBE-KJM000 | KOBE-KJM090 |
| 15 | Chi-Chi 1999 | CHY006 | 1182 | CHICHI-CHY006-N | CHICHI-CHY006-W |

받은 뒤 확인: `cd 페이퍼/코드 && python check_model.py` → 첫 줄에 "입력: PEER (원문 표 2), 15쌍"이 나오면 성공입니다. 빠진 성분이 있으면 이름이 표시됩니다.

## 2026-10-21 현재: 공개 GitHub 저장소에서 받은 8쌍

NGA-West2와 CESMD 모두 접속이 안 되어, 연구자들이 공개 저장소에 올려 둔 PEER 원본 `.AT2` 파일을 받았습니다(헤더와 최대 가속도가 NGA 값과 같음을 확인함).

| 번호 | 출처 저장소 |
|---|---|
| 1, 4 | jfayaz/Parse_NGAWEST2_GMs_to_AT2_-_Spectra_to_txt |
| 2 | kmscse/peer_ground_motion_time_series_records |
| 3 | nc-hsu/phd (헤더가 파일 끝에 있어 앞으로 옮김. 360 파일 헤더에 "230"이라 적혀 있음, PGA 0.48 g) |
| 11 | VSilva/DBELA (옛 PEER 형식, 파일명 앞에 `IMPVALL_` 붙임) |
| 13 | nkalauni/low-cost-base-isolation |
| 14 | ChairOfStructuralMechanicsTUM/Mechanics_Apps |
| 15 | tongcezhou/PCE_NARX |

없음: 5(ECC092), 6(E10), 7(AGR273), 8(E05230), 9(E07), 10(E08), 12(HVP). 5·7·8은 한쪽 성분만 있음. 6·9·10·12는 여진(A-) 기록만 찾았는데, 본진이 아니어서 쓰지 않음.

## 크기 조정
- 원문: 최대 가속도를 35 cm/s²(중국 기준 소규모 지진)로 정규화
- 우리 처리: **X · Y 성분을 각각** 최대 35 cm/s²로 맞춤 (원문이 성분별인지 쌍 전체인지 밝히지 않음 → 무제어 응답을 원문 표 4~6과 비교해 결정)

## 2026-11-04: FEMA P695 세트 추가 (9주차 독립 시험용)

NGA-West2에서 스케일 없는 원본(Unscaled)으로 받은 FEMA P695 원거리(`PEER/FEMA_FF/`, 20쌍)·근단층(`PEER/FEMA_NF/`, 27쌍) 기록입니다. 수평 2성분만 넣었고, 검색 결과 원본은 각 폴더의 `_SearchResults*.csv`입니다.
원문 15쌍과 겹치는 RSN 174·182는 넣지 않았습니다. RSN 829(Cape Mendocino, Rio Dell)는 받지 못했습니다.

사건 단위 분할은 `PEER/record_manifest.csv`의 `split` 열에 있습니다.

| split | 쌍 | 사건 | 뜻 |
|---|---|---|---|
| `test` | 25 | 12 | 원문과 8주차 개발에 쓰지 않은 사건. 규칙·모델을 고정한 뒤 한 번만 평가 |
| `dev_paper_event` | 18 | 4 | 원문 표 2와 같은 사건(Imperial Valley, Northridge, Kobe, Chi-Chi). 개발용 |
| `excluded_week8` | 4 | 3 | 8주차 규칙 선정·AI 학습에 쓴 사건(San Fernando, Düzce, Manjil) |

⚠️ 8주차 학습 자료의 "Düzce 1999"가 Kocaeli 지진의 Düzce 관측소 기록(RSN 1158)이라면 Kocaeli도 `test`에서 빼야 합니다(확인 필요).
