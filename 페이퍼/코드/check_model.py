# -*- coding: utf-8 -*-
"""재현 1단계 점검.
  1) 고유진동수 · 1차 모드 질량 참여율 → 원문 표 1, 83.76%
  2) 지진 입력별 무제어 / 수동 / S-TLCD / RS-TLCD 저감률 (원문 표 7 형식)
     PEER 15쌍이 `페이퍼/입력/PEER/`에 있으면 그것으로, 없으면 보유 3쌍으로.
사용: python check_model.py [--zeta 0.1] [--cos2] [--held]
"""
import argparse, json, os, time
import numpy as np
import rstlcd as R
import records

ap = argparse.ArgumentParser()
ap.add_argument('--zeta', type=float, default=None, help='TLCD 감쇠비를 식 (24) 대신 고정 (민감도용)')
ap.add_argument('--cos2', action='store_true', help='k_dx에 cosθ를 한 번 더 곱함 (원문 식 20 그대로, 처리 #2)')
ap.add_argument('--held', action='store_true', help='PEER가 있어도 보유 기록만 사용')
ap.add_argument('--dt', type=float, default=0.01)
args = ap.parse_args()

# ── 1) 고유진동수 ──
M, K = R.structure()
f, phi = R.modal(M, K)
print('고유진동수 [Hz]  (3차원 연성 모델, 처음 12개)')
print('  ', ' '.join(f'{x:.4f}' for x in f[:12]))
fx, _ = R.modal(M[:R.N], K[:R.N, :R.N])
print('X 방향만 (연성 제외)  vs 원문 표 1')
for i in range(10):
    print(f'  {i+1:2d}차  {fx[i]:.4f}   표 1 {R.F_TABLE1[i]:.4f}   차이 {100*(fx[i]/R.F_TABLE1[i]-1):+.2f}%')
rx = np.r_[np.ones(R.N), np.zeros(2 * R.N)]
gam = (phi.T @ (M * rx)) ** 2                    # 질량 정규화 모드 → 유효질량
part = gam / (M[:R.N].sum())
j = int(np.argmax(part))
print(f'X 방향 유효질량이 가장 큰 모드: {j+1}차 {f[j]:.4f} Hz, 참여율 {100*part[j]:.2f}%  (원문 83.76%)')
print(f'1~3차 X 참여율: {", ".join(f"{100*p:.2f}%" for p in part[:3])}  합 {100*part[:3].sum():.2f}%')

# ── 2) 지진 응답 ──
pairs, missing = ([], ['(보유 기록 강제)']) if args.held else records.paper_pairs(args.dt)
if pairs:
    src = 'PEER (원문 표 2)'; runs = [(f'{no:2d} {st}', x, y) for no, st, x, y in pairs]
else:
    src = '보유 기록'; runs = records.held_pairs(args.dt)
print(f'\n입력: {src}, {len(runs)}쌍, 각 성분 최대 35 cm/s²' + (f'  (PEER 없음: {len(missing)}개 성분)' if missing and not pairs else ''))
print(f'설정: TLCD 감쇠 = {"식 (24)" if args.zeta is None else f"고정 ζ={args.zeta}"}, k_dx cosθ {"두 번" if args.cos2 else "한 번"}, dt={args.dt}')

cases = ['passive', 'stlcd', 'rstlcd']
keys = ['ux_max', 'uy_max', 'th_max', 'ux_rms', 'uy_rms', 'th_rms']
allred = {c: [] for c in cases}; rows = []
t0 = time.time()
for name, x, y in runs:
    base = R.metrics(R.simulate(x, y, args.dt, 'none'))
    row = {'name': name, 'none': base}
    for c in cases:
        o = R.simulate(x, y, args.dt, c, zeta_override=args.zeta, cos_twice=args.cos2)
        red = R.reduction(R.metrics(o), base); allred[c].append(red); row[c] = red
        if c == 'rstlcd':
            row['rs_f_range'] = [float(o['f_dev'][1:].min()), float(o['f_dev'][1:].max())]
            row['rs_theta_deg'] = [float(np.rad2deg(o['theta']).min()), float(np.rad2deg(o['theta']).max())]
    rows.append(row)
    print(f'  {name:32s} 무제어 X {100*base["ux_max"]:.3f} cm, Y {100*base["uy_max"]:.3f} cm, θ {1e4*base["th_max"]:.3f}e-4 rad'
          f' | RS X최대 {row["rstlcd"]["ux_max"]:+.1f}%  X RMS {row["rstlcd"]["ux_rms"]:+.1f}%  ({time.time()-t0:.0f}s)')

print('\n평균 저감률 [%]   X최대   Y최대   θ최대   X RMS   Y RMS   θ RMS')
for c in cases:
    m = {k: np.mean([r[k] for r in allred[c]]) for k in keys}
    print(f'  {c:8s}      ' + '  '.join(f'{m[k]:6.2f}' for k in keys))
print('원문 표 7')
for c, v in (('passive', [15.39, 11.45, 9.85, 33.54, 14.33, 11.43]), ('stlcd', [13.29, 10.40, 9.52, 33.46, 16.81, 13.06]),
             ('rstlcd', [15.48, 13.74, 11.50, 38.03, 18.00, 16.03])):
    print(f'  {c:8s}      ' + '  '.join(f'{x:6.2f}' for x in v))

os.makedirs('results', exist_ok=True)
tag = ('peer' if pairs else 'held') + (f'_z{args.zeta}' if args.zeta is not None else '') + ('_cos2' if args.cos2 else '')
json.dump(rows, open(f'results/check_{tag}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n저장: results/check_{tag}.json')
