# -*- coding: utf-8 -*-
"""v3 §4: 지진 자료 세 묶음 manifest (A 원문 공통 / B 개발 11 / C 독립 신규).
원문 표 2의 15쌍마다 보유 여부, 원본 파일의 헤더·단위·샘플링·길이·원본 PGA·sha256, 처리본(dt 0.01 CSV) sha256과 성분별 배율을 기록한다.
동일 사건명만으로 같은 기록이라고 판단하지 않는다: 헤더의 관측소·성분과 원문 표 2의 이름을 대조해 header_match에 적는다.
사용: python build_record_manifest.py  → record_manifest.csv
"""
import csv, glob, hashlib, os, re
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MAT = os.path.join(ROOT, 'predictive_control_matlab')
PEER = os.path.join(ROOT, '페이퍼', '입력', 'PEER')

PAIRS = [  # 원문 표 2
 (1, 'El Centro Array #11', 'IMPVALL-E11140', 'IMPVALL-E11230'), (2, 'Aeropuerto Mexicali', 'IMPVALL-AEP045', 'IMPVALL-AEP315'),
 (3, 'El Centro Differential Array', 'IMPVALL-EDA270', 'IMPVALL-EDA360'), (4, 'Brawley Airport', 'IMPVALL-BRA225', 'IMPVALL-BRA315'),
 (5, 'EC County Center FF', 'IMPVALL-ECC002', 'IMPVALL-ECC092'), (6, 'El Centro Array #10', 'IMPVALL-E10050', 'IMPVALL-E10320'),
 (7, 'Agrarias', 'IMPVALL-AGR003', 'IMPVALL-AGR273'), (8, 'El Centro Array #5', 'IMPVALL-E05140', 'IMPVALL-E05230'),
 (9, 'El Centro Array #7', 'IMPVALL-E07140', 'IMPVALL-E07230'), (10, 'El Centro Array #8', 'IMPVALL-E08140', 'IMPVALL-E08230'),
 (11, 'El Centro Array #3', 'IMPVALL-E03140', 'IMPVALL-E03230'), (12, 'Holtville Post Office', 'IMPVALL-HVP225', 'IMPVALL-HVP315'),
 (13, 'Pacoima Dam', 'NORTHR-PAC175', 'NORTHR-PAC265'), (14, 'KJMA', 'KOBE-KJM000', 'KOBE-KJM090'), (15, 'CHY006', 'CHICHI-CHY006-N', 'CHICHI-CHY006-W')]
SRC = {1: 'jfayaz/Parse_NGAWEST2_GMs_to_AT2_-_Spectra_to_txt', 2: 'kmscse/peer_ground_motion_time_series_records', 3: 'nc-hsu/phd',
       4: 'jfayaz/Parse_NGAWEST2_GMs_to_AT2_-_Spectra_to_txt', 11: 'VSilva/DBELA (옛 PEER 형식)', 13: 'nkalauni/low-cost-base-isolation',
       14: 'ChairOfStructuralMechanicsTUM/Mechanics_Apps', 15: 'tongcezhou/PCE_NARX'}   # 페이퍼/입력/README.md (2026-10-21)
MISSING_NOTE = {5: 'ECC002만 보유(ECC092 없음)', 6: '본진 기록 없음(여진 A- 기록만 발견, 사용 안 함)', 7: 'AGR003만 보유(AGR273 없음)',
                8: 'E05140만 보유(E05230 없음)', 9: '본진 기록 없음(여진만)', 10: '본진 기록 없음(여진만)', 12: '본진 기록 없음(여진만)'}

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()[:16]

def key(s): return re.sub(r'[^A-Z0-9]', '', s.upper())

def find(token):
    ev, comp = token.split('-', 1)
    hits = [p for p in glob.glob(os.path.join(PEER, '**', '*.AT2'), recursive=True) if key(ev) in key(os.path.basename(p)) and key(comp) in key(os.path.basename(p))]
    return hits[0] if hits else None

def read_at2(p):
    lines = open(p, encoding='latin-1').read().splitlines()
    npts = dt = None
    for j, ln in enumerate(lines[:10]):
        m = re.search(r'NPTS\s*=\s*(\d+)\s*,\s*DT\s*=\s*([0-9.Ee+-]+)', ln)
        if m: npts, dt, hdr_end = int(m.group(1)), float(m.group(2)), j; break
        m = re.match(r'\s*(\d+)\s+([0-9.Ee+-]+)\s', ln)
        if m and j >= 3: npts, dt, hdr_end = int(m.group(1)), float(m.group(2)), j; break
    v = np.array(' '.join(lines[hdr_end + 1:]).split(), float)[:npts]
    unit = 'g' if any('UNITS OF G' in l.upper() for l in lines[:6]) else 'g(가정)'
    return dict(title=lines[1].strip(), npts=npts, dt=dt, duration_s=(npts - 1) * dt, pga_g=float(np.abs(v).max()), unit=unit, n_read=len(v))

def header_match(title, station, comp):
    """헤더 문자열에서 관측소 이름과 성분(각도 또는 방향 문자)이 원문 표 2의 이름과 같은지."""
    t = key(title)
    st_ok = key(station.replace('#', '')).replace('ARRAY', '') in t.replace('ARRAY', '') or key(station.split()[0]) in t
    c = comp.split('-', 1)[1]
    m = re.search(r'(\d{3})$', c)
    if m:   # 각도: 헤더의 숫자(날짜·관측소 번호 제외, 마지막 쉼표 구간과 괄호 앞)에 같은 각도가 있는지
        ang = int(m.group(1)); tail = re.sub(r'\(.*?\)', '', title).split(',')[-1]
        cmp_ok = ang in [int(x) for x in re.findall(r'\d+', tail)]
    else:   # 방향 문자 (CHY006-N)
        cmp_ok = title.strip().upper().endswith(c[-1].upper())
    return st_ok, cmp_ok

rows = []
man = {r['record_id']: r for r in csv.DictReader(open(os.path.join(MAT, 'data', 'record_manifest.csv'), encoding='utf-8-sig'))}
for no, st, tx, ty in PAIRS:
    rid = 'PEER%02d' % no
    px, py = find(tx), find(ty)
    base = dict(group='A 원문 공통 기록', paper_no=no, record_id=rid if (px and py) else '', station=st, x_name=tx, y_name=ty, source_repo=SRC.get(no, ''))
    if not (px and py):
        base.update(status='미확보', note=MISSING_NOTE.get(no, ''), usable_for_reproduction='아니오 (빈자리를 다른 관측소·여진·성분으로 채우지 않음)')
        rows.append(base); continue
    ix, iy = read_at2(px), read_at2(py)
    pr = [os.path.join(MAT, 'data', 'records', 'dt0.01', rid + '.csv')]
    arr = np.loadtxt(pr[0], delimiter=',', skiprows=1)
    stx, cx = header_match(ix['title'], st, tx); sty, cy = header_match(iy['title'], st, ty)
    base.update(status='보유', x_file=os.path.relpath(px, ROOT), y_file=os.path.relpath(py, ROOT), x_sha256_16=sha(px), y_sha256_16=sha(py),
                x_header=ix['title'], y_header=iy['title'], x_npts=ix['npts'], y_npts=iy['npts'], x_dt_s=ix['dt'], y_dt_s=iy['dt'],
                x_duration_s=round(ix['duration_s'], 3), y_duration_s=round(iy['duration_s'], 3), unit='g (AT2 헤더)', x_raw_pga_g=round(ix['pga_g'], 5), y_raw_pga_g=round(iy['pga_g'], 5),
                header_station_match='예' if (stx and sty) else '확인 필요', header_component_match='예' if (cx and cy) else '확인 필요',
                processed_csv_dt0p01=os.path.relpath(pr[0], ROOT), processed_sha256_16=sha(pr[0]), processed_n_samples=arr.shape[0],
                processed_x_peak_mps2=round(float(np.abs(arr[:, 1]).max()), 6), processed_y_peak_mps2=round(float(np.abs(arr[:, 2]).max()), 6),
                scale_x=round(0.35 / (ix['pga_g'] * 9.81), 5), scale_y=round(0.35 / (iy['pga_g'] * 9.81), 5),
                note=man[rid]['filtering'], usable_for_reproduction='예 (성분별 35 cm/s² 배율은 가정, 원문 미명시)')
    rows.append(base)
# B: 개발 추가 3기록 + 원문 공통 8쌍도 개발 평가 11기록에 포함
for rid in ('ElCentro_1940', 'Pohang_2017_BUS2', 'Gyeongju_2016_CHJ2'):
    m = man[rid]; p = os.path.join(MAT, 'data', 'records', 'dt0.01', rid + '.csv'); arr = np.loadtxt(p, delimiter=',', skiprows=1)
    rows.append(dict(group='B 개발 추가 기록(원문 15쌍 아님)', paper_no='', record_id=rid, station=m['station'], x_name=m['x_component'], y_name=m['y_component'],
                     source_repo=m['source'], status='보유', unit=m['unit_raw'], processed_csv_dt0p01=os.path.relpath(p, ROOT), processed_sha256_16=sha(p),
                     processed_n_samples=arr.shape[0], processed_x_peak_mps2=round(float(np.abs(arr[:, 1]).max()), 6), processed_y_peak_mps2=round(float(np.abs(arr[:, 2]).max()), 6),
                     note=m['filtering'], usable_for_reproduction='아니오 (원문 기록 아님, 개발 확대 평가 전용)'))
rows.append(dict(group='C 신규 독립 기록', paper_no='', record_id='', status='미확보', note='학습·구조·checkpoint 선택에 쓰지 않은 사건을 마감 전에 확보·검증하지 못함 → 미실행. B를 C로 바꿔 부르지 않음',
                 usable_for_reproduction='해당 없음'))
fields = ['group', 'paper_no', 'record_id', 'station', 'x_name', 'y_name', 'status', 'source_repo', 'x_file', 'y_file', 'x_sha256_16', 'y_sha256_16', 'x_header', 'y_header',
          'x_npts', 'y_npts', 'x_dt_s', 'y_dt_s', 'x_duration_s', 'y_duration_s', 'unit', 'x_raw_pga_g', 'y_raw_pga_g', 'header_station_match', 'header_component_match',
          'processed_csv_dt0p01', 'processed_sha256_16', 'processed_n_samples', 'processed_x_peak_mps2', 'processed_y_peak_mps2', 'scale_x', 'scale_y', 'usable_for_reproduction', 'note']
with open(os.path.join(HERE, 'record_manifest.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
nA = sum(1 for r in rows if r['group'].startswith('A') and r['status'] == '보유')
print('원문 15쌍 중 보유', nA, '쌍, 미확보', 15 - nA, '쌍; B 추가 3기록; C 없음')
for r in rows:
    if r['group'].startswith('A') and r['status'] == '보유':
        print(r['paper_no'], r['record_id'], r['station'], 'dt', r['x_dt_s'], r['y_dt_s'], 'len', r['x_duration_s'], r['y_duration_s'], 'hdr', r['header_station_match'], r['header_component_match'])
