# -*- coding: utf-8 -*-
"""개발 기록 11개(사건 7개)를 MATLAB용 CSV로 내보낸다 (7주차 재현 전처리 그대로).

전처리는 페이퍼/코드/records.py(원본, 수정 없음)를 그대로 호출한다:
  평균 제거 → 선형 보간 재표본화(dt) → 끝에 10 s 0 → 성분별 최대 0.35 m/s² 정규화.
  성분별 정규화는 전체 기록의 최대값을 쓰므로 '7주차 재현용 일정 PGA 트랙'의 자료 정의이며 온라인 전처리가 아니다.
사용: python export_records.py            (dt 0.01, 0.005 둘 다)
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, '페이퍼', '코드'))
import records as rec

EVENT_OF_TOKEN = {'IMPVALL': 'ImperialValley1979', 'NORTHR': 'Northridge1994', 'KOBE': 'Kobe1995', 'CHICHI': 'ChiChi1999'}
HELD_META = {'El Centro 1940': ('ElCentro_1940', 'ElCentro1940', 'El Centro (Imperial Valley 1940)', 'elcentro_NS.txt', 'elcentro_EW.txt', 'g', '6주차 보유기록'),
             '포항 2017 BUS2': ('Pohang_2017_BUS2', 'Pohang2017', 'BUS2', 'pohang_BUS2_BHE.txt', 'pohang_BUS2_BHN.txt', 'm/s2', '기상청 (6주차 보유기록)'),
             '경주 2016 CHJ2': ('Gyeongju_2016_CHJ2', 'Gyeongju2016', 'CHJ2', 'gyeongju_CHJ2_BHE.txt', 'gyeongju_CHJ2_BHN.txt', 'm/s2', '기상청 (6주차 보유기록)')}
MAG = {'ImperialValley1979': '6.53', 'Northridge1994': '6.69', 'Kobe1995': '6.9', 'ChiChi1999': '7.62',
       'ElCentro1940': '6.95', 'Pohang2017': '5.4', 'Gyeongju2016': '5.8'}   # 일반적으로 인용되는 규모(원문 출처 확인 전, 분석에 쓰지 않음)

def write(path, x, y, dt):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['t_s', 'agx_mps2', 'agy_mps2'])
        for i in range(len(x)):
            w.writerow([f'{i * dt:.6f}', f'{x[i]:.10e}', f'{y[i]:.10e}'])

def main():
    rows = []
    for dt in (0.01, 0.005):
        tag = f'dt{dt:g}'
        od = os.path.join(HERE, '..', 'data', 'records', tag); os.makedirs(od, exist_ok=True)
        paper, missing = rec.paper_pairs(dt)
        tok = {no: (tx, ty) for no, st, tx, ty in rec.PAPER_PAIRS}
        for no, st, x, y in paper:
            rid = f'PEER{no:02d}'; ev = EVENT_OF_TOKEN[tok[no][0].split('-')[0]]
            write(os.path.join(od, rid + '.csv'), x, y, dt)
            if dt == 0.01:
                rows.append(dict(record_id=rid, event_id=ev, station=st, x_component=tok[no][0], y_component=tok[no][1],
                                 source='PEER NGA-West2 (.AT2, 페이퍼/입력/PEER)', unit_raw='g', dt_raw='AT2 header', magnitude_unverified=MAG[ev],
                                 distance_type='unknown', distance_km='unknown', filtering='PEER 처리본(원 처리 이력 미기록); 평균 제거·선형 재표본화·성분별 PGA 0.35 m/s²',
                                 n_samples_dt001=len(x), split='dev'))
        for name, x, y in rec.held_pairs(dt):
            rid, ev, st, fx, fy, unit, src = HELD_META[name]
            write(os.path.join(od, rid + '.csv'), x, y, dt)
            if dt == 0.01:
                rows.append(dict(record_id=rid, event_id=ev, station=st, x_component=fx, y_component=fy, source=src, unit_raw=unit,
                                 dt_raw='file', magnitude_unverified=MAG[ev], distance_type='unknown', distance_km='unknown',
                                 filtering=('한국 기록: 최대값 5% 문턱 5 s 전부터 60 s 절취(전체 기록 사용, 오프라인); ' if unit != 'g' else '') + '평균 제거·선형 재표본화·성분별 PGA 0.35 m/s²',
                                 n_samples_dt001=len(x), split='dev'))
        if missing: print(tag, '없는 PEER 성분:', len(missing))
    with open(os.path.join(HERE, '..', 'data', 'record_manifest.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), 'records,', len({r["event_id"] for r in rows}), 'events')

if __name__ == '__main__':
    main()
