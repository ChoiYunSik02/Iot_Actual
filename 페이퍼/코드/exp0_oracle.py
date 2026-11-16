# -*- coding: utf-8 -*-
"""실험 0 — Oracle 상한: 지진 전에 '정답' 진동수 · 회전각을 알고 미리 맞춰 두면 얼마나 더 줄어드나.
  E0 무제어 / E1 수동 / E1b 수동 디튜닝 / ES 원문 S-TLCD ×2 / E2 원문 RS-TLCD(웨이블릿 + on-off 감쇠 + 회전) / E4 Oracle RS-TLCD
  Oracle = 기록마다 (f, θ) 격자(장치 범위 ±5% × 0~90°) 전체를 돌려 6개 지표 평균 저감률이 가장 큰 값을 t = 0부터 고정.
  E1b = 수동을 원래 건물에서 찾은 최적 고정값으로 미리 디튜닝한 것 — 예측 없이 얻는 기준선.
  감쇠: 기본은 식 (24) × 30 (수동이 원문 표 7과 맞도록 보정, κ에 따른 가변 감쇠 살아 있음).
        --zeta 0.1을 주면 감쇠비 10% 고정 (κ 무시 → 가변 감쇠 꺼짐, 이전 실험).
  --kscale: 건물 강성 배율 (실험 1: 손상 · 하중 변화로 건물 진동수가 √k배가 된 경우). 장치 설계값은 원래 건물 그대로.
사용: python exp0_oracle.py [--nf 7] [--nth 7] [--cscale 30 | --zeta 0.1] [--kscale 0.81]
"""
import argparse, json, os, time
from multiprocessing import Pool
import numpy as np
import rstlcd as R
import records

ap = argparse.ArgumentParser()
ap.add_argument('--nf', type=int, default=7)
ap.add_argument('--nth', type=int, default=7)
ap.add_argument('--zeta', type=float, default=None)
ap.add_argument('--cscale', type=float, default=30.0)
ap.add_argument('--dt', type=float, default=0.01)
ap.add_argument('--kscale', type=float, default=1.0)
ap.add_argument('--f-detuned', type=float, default=None, help='기본: 식 24 보정 0.3204, ζ 고정 0.31 Hz')
args = ap.parse_args()
if args.f_detuned is None:
    args.f_detuned = 0.31 if args.zeta is not None else 0.3204
CASES = ('E1', 'E1b', 'ES', 'E2', 'E4')
NAMES = ('수동', '수동 디튜닝', '원문 S-TLCD', '원문 RS', 'Oracle RS')


def run(job):
    key, x, y, kw = job
    if kw.pop('oracle', False):          # 람다는 프로세스 사이로 못 넘겨서 여기서 만듦
        f, th = kw['f0'], kw['theta0']; kw.update(rs_freq=lambda t, s: f, rs_theta=lambda t, s: th)
    return key, R.metrics(R.simulate(x, y, args.dt, zeta_override=args.zeta, c_scale=args.cscale, k_scale=args.kscale, **kw))


def score(red):
    return float(np.mean(list(red.values())))


if __name__ == '__main__':
    pairs, _ = records.paper_pairs(args.dt)
    F = np.linspace(*R.F_RANGE, args.nf); TH = np.deg2rad(np.linspace(0, 90, args.nth))
    jobs = []
    for no, st, x, y in pairs:
        jobs += [((no, 'E0'), x, y, dict(case='none')), ((no, 'E1'), x, y, dict(case='passive')),
                 ((no, 'E1b'), x, y, dict(case='passive', f0=args.f_detuned)), ((no, 'ES'), x, y, dict(case='stlcd')), ((no, 'E2'), x, y, dict(case='rstlcd'))]
        for f in F:
            for th in TH:
                jobs.append(((no, 'E4', float(f), float(th)), x, y, dict(case='rstlcd', f0=f, theta0=th, oracle=True)))
    t0 = time.time()
    with Pool() as pool:
        res = dict(pool.map(run, jobs, chunksize=4))
    print(f'{len(jobs)}회 계산, {time.time() - t0:.0f}s')
    print(f'건물 강성 ×{args.kscale} → 1차 진동수 {R.F0 * np.sqrt(args.kscale):.4f} Hz (장치 범위 {R.F_RANGE[0]}~{R.F_RANGE[1]} Hz)')

    keys = ['ux_max', 'uy_max', 'th_max', 'ux_rms', 'uy_rms', 'th_rms']
    rows, tab = [], {c: [] for c in CASES}
    print('\n번호 관측소                               E1 수동  E1b 디튜닝  ES 원문S   E2 원문RS  E4 Oracle  (6지표 평균 %)   Oracle f [Hz], θ [°]')
    for no, st, _, _ in pairs:
        base = res[(no, 'E0')]
        red = {c: R.reduction(res[(no, c)], base) for c in CASES[:4]}
        grid = {k[2:]: R.reduction(m, base) for k, m in res.items() if k[0] == no and k[1] == 'E4'}
        best = max(grid, key=lambda k: score(grid[k])); red['E4'] = grid[best]
        for c in tab: tab[c].append(red[c])
        print(f'{no:3d}  {st:30s} ' + '  '.join(f'{score(red[c]):9.2f}' for c in CASES)
              + f'        {best[0]:.4f}, {np.rad2deg(best[1]):.0f}')
        rows.append({'no': no, 'station': st, 'none': base, **red, 'oracle_f': best[0], 'oracle_theta_deg': float(np.rad2deg(best[1])),
                     'grid': [[k[0], float(np.rad2deg(k[1])), score(v)] for k, v in grid.items()]})

    print('\n평균 저감률 [%]   X최대   Y최대   θ최대   X RMS   Y RMS   θ RMS   평균')
    for c, name in zip(CASES, NAMES):
        m = [np.mean([r[k] for r in tab[c]]) for k in keys]
        print(f'  {name:10s}  ' + '  '.join(f'{v:6.2f}' for v in m) + f'  {np.mean(m):6.2f}')

    os.makedirs('results', exist_ok=True)
    tag = 'exp1' + (f'_z{args.zeta}' if args.zeta is not None else f'_c{args.cscale:g}') + f'_k{args.kscale}'
    json.dump(rows, open(f'results/{tag}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n저장: results/{tag}.json')
