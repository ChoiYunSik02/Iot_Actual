# -*- coding: utf-8 -*-
"""원문(Fu et al. 2025) 표 4-6을 PDF 텍스트에서 읽어 paper_tables_4_6.csv로 저장하고, 표 7(15쌍 평균)과 맞는지 확인한다.
사용: python extract_paper_tables.py  (pdftotext 필요)
단위: X·Y 변위 cm, 비틀림각 1e-4 rad. 열: no, index, without, passive, s_tlcd, rs_tlcd
"""
import re, subprocess, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.abspath(os.path.join(HERE, '..', '..', '..', '논문', '06_JOBE2025_rotating_semiactive_TLCD.pdf'))
txt = subprocess.run(['pdftotext', '-layout', PDF, '-'], capture_output=True, text=True).stdout
lines = txt.splitlines()
tables = {'Table 4': ('X', 'cm'), 'Table 5': ('Y', 'cm'), 'Table 6': ('TH', '1e-4 rad')}
rows = []
for tname, (comp, unit) in tables.items():
    i = next(k for k, l in enumerate(lines) if l.strip().startswith(tname) and k > 600)   # 본문 표 (목차·언급 제외)
    n = 0
    for l in lines[i:i + 40]:
        if n == 15: break
        m = re.match(r'^\s*(\d{1,2})\s+((?:-?\d+\.\d+\s+){7}-?\d+\.\d+)\s*$', l)
        if not m: continue
        no = int(m.group(1)); v = list(map(float, m.group(2).split()))
        for j, (idx, vals) in enumerate((('max', v[0:4]), ('rms', v[4:8]))):
            rows.append(dict(no=no, component=comp, stat=idx, unit=unit, without=vals[0], passive=vals[1], s_tlcd=vals[2], rs_tlcd=vals[3]))
        n += 1
    assert n == 15, (tname, n)
out = os.path.join(HERE, 'paper_tables_4_6.csv')
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
# 표 7 확인: 기록별 저감률의 평균(15쌍)
t7 = {'passive': [15.39, 11.45, 9.85, 33.54, 14.33, 11.43], 's_tlcd': [13.29, 10.40, 9.52, 33.46, 16.81, 13.06], 'rs_tlcd': [15.48, 13.74, 11.50, 38.03, 18.00, 16.03]}
order = [('X', 'max'), ('Y', 'max'), ('TH', 'max'), ('X', 'rms'), ('Y', 'rms'), ('TH', 'rms')]
ok = True
for case, ref in t7.items():
    mine = []
    for comp, st in order:
        r = [100 * (1 - x[case] / x['without']) for x in rows if x['component'] == comp and x['stat'] == st]
        mine.append(sum(r) / len(r))
    d = max(abs(a - b) for a, b in zip(mine, ref))
    print(case, ' '.join(f'{v:.2f}' for v in mine), '| 표 7과 최대 차 %.3f' % d)
    ok = ok and d < 0.06
print('표 4-6 전사 ↔ 표 7 일치:', ok)
sys.exit(0)
