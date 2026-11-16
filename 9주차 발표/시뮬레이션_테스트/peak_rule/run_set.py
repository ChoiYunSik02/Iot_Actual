"""9주차 계획 4절의 비교 실행: U · R · FIX45 · PEAK(동결) · PEAK 변형 2개를 기록 세트 하나에 돌린다.

사용:  python run_set.py paper15   # 원문 15쌍 (회귀 확인: U, R, PEAK가 8주차·v19 값과 같아야 함)
       python run_set.py dev       # record_manifest.csv split=dev_paper_event (리허설)
       python run_set.py test      # split=test, 9주차 계획 4절 그대로 1회만

peak_rule.py의 Peak 클래스는 수정하지 않고 가져다 쓴다(동결본).
전처리는 원문 15쌍과 같다: 성분마다 최대 가속도 0.35 m/s², 입력 dt 그대로, h1=X, h2=Y.
"""
import sys, os, re, csv, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from scipy.linalg import expm

import peak_rule as pr  # sys.path 설정과 Peak · Tracked · RPolicy를 함께 가져온다
from peak_rule import Plant, simulate, metrics, Tracked, RPolicy, Peak, W8
from model import build, N  # reproduction_v2

ROOT = os.path.abspath(os.path.join(W8, '..', '..'))
PEER = os.path.join(ROOT, '페이퍼', '입력', 'PEER')
PAPER15 = os.path.join(W8, 'peer_records_table2')


class Fix45(Tracked):
    """회전판 45° 고정 (k=0에 45° 지령, 30°/s로 도달). 펌프·밸브는 원문."""
    def decide(s, ob, hx, hy, th_act):
        s.track(th_act)
        out = [(kind, {'f': cmd['f']}, rec) for kind, cmd, rec in RPolicy.decide(s, ob, hx, hy, th_act)]
        if ob.k == 0: out.append(('slow', {'tht': np.pi / 4}, (3, 0, 0.0, 45.0, 45.0, 0, 0)))
        return out


VARIANTS = {
    'R': lambda dt: Tracked(dt),
    'FIX45': lambda dt: Fix45(dt),
    'PEAK': lambda dt: Peak(dt),
    'PEAK_maxabs': lambda dt: Peak(dt, mag='maxabs'),
    'PEAK_pull1': lambda dt: Peak(dt, pull=1.0),  # 피크 순간 방향 그대로
}


def read_at2(path):
    L = open(path).read().split('\n')
    m = re.search(r'NPTS=\s*(\d+),\s*DT=\s*([\d.]+)', L[3]); n = int(m.group(1))
    return np.array(' '.join(L[4:]).split(), float)[:n] * 9.80665, float(m.group(2))


def record_list(name):
    """[(id, event, group, path_x, path_y)]"""
    if name == 'paper15':
        rows = list(csv.DictReader(open(os.path.join(PAPER15, 'records_table2.csv'), encoding='utf-8')))
        return [(f"P{r['no']}", r['event'], 'paper', os.path.join(PAPER15, r['x_file']), os.path.join(PAPER15, r['y_file']))
                for r in rows]
    split = {'dev': 'dev_paper_event', 'test': 'test', 'week8': 'excluded_week8', 'test2': 'test2'}[name]
    rows = [r for r in csv.DictReader(open(os.path.join(PEER, 'record_manifest.csv'), encoding='utf-8-sig'))
            if r['split'] == split]
    grp = lambda r: 'far' if r['set'] == 'FEMA_FF' else ('near_pulse' if r['pulse_tp_s'] else 'near_nonpulse')
    return [(f"RSN{r['rsn']}", r['event'], grp(r), os.path.join(PEER, r['set'], r['h1']), os.path.join(PEER, r['set'], r['h2']))
            for r in rows]


def load(rec):
    ax, dt = read_at2(rec[3]); ay, dt2 = read_at2(rec[4])
    assert abs(dt - dt2) < 1e-12, rec
    n = min(len(ax), len(ay))
    return ax[:n] * 0.35 / abs(ax).max(), ay[:n] * 0.35 / abs(ay).max(), dt


def uncontrolled(ax, ay, dt):
    """무제어: 건물만(식 19 문자 그대로), 건물 1·2차 모드 Rayleigh 2 %, ZOH. MATLAB run_v2b_check.m과 같은 정의."""
    M, K = build('lit'); n = 3 * N
    w = np.sqrt(np.sort(np.linalg.eigvals(np.linalg.solve(M, K)).real)[:2])
    a0, a1 = np.linalg.solve([[1 / (2 * w[0]), w[0] / 2], [1 / (2 * w[1]), w[1] / 2]], [0.02, 0.02])
    C = a0 * M + a1 * K; Mi = np.linalg.inv(M)
    A = np.block([[np.zeros((n, n)), np.eye(n)], [-Mi @ K, -Mi @ C]])
    E = np.zeros((n, 2)); E[:N, 0] = 1; E[N:2 * N, 1] = 1
    B = np.vstack([np.zeros((n, 2)), -E])
    Z = np.zeros((2 * n + 2, 2 * n + 2)); Z[:2 * n, :2 * n] = A * dt; Z[:2 * n, 2 * n:] = B * dt; Ez = expm(Z)
    Ad, Bd = Ez[:2 * n, :2 * n], Ez[:2 * n, 2 * n:]
    x = np.zeros(2 * n); y = np.empty((len(ax), 3)); idx = [N - 1, 2 * N - 1, 3 * N - 1]
    for k in range(len(ax)):
        y[k] = x[idx]; x = Ad @ x + Bd @ np.r_[ax[k], ay[k]]
    return metrics(y)


_plants = {}


def job(args):
    name, rec = args
    ax, ay, dt = load(rec)
    if name == 'U': return name, rec[0], uncontrolled(ax, ay, dt).tolist(), 0.0, 0
    if dt not in _plants: _plants[dt] = Plant(dt)
    pol = VARIANTS[name](dt)
    y, _, _ = simulate(_plants[dt], ax, ay, pol)
    return name, rec[0], metrics(y).tolist(), float(np.rad2deg(pol.rot)), getattr(pol, 'n_peak', 0)


def boot_ci(d, n=10000, seed=8500):
    """사건 단위 paired bootstrap: 사건별 차이 d의 평균에 대한 95 % 구간."""
    g = np.random.default_rng(seed); d = np.asarray(d)
    m = d[g.integers(0, len(d), (n, len(d)))].mean(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def summarize(recs, res, drop_events=()):
    recs = [r for r in recs if r[1] not in drop_events]
    ids = [r[0] for r in recs]; events = sorted({r[1] for r in recs})
    U = np.array([res[('U', i)][0] for i in ids])
    S = {}
    for name in VARIANTS:
        red = (1 - np.array([res[(name, i)][0] for i in ids]) / U) * 100
        r6 = red.mean(1)
        ev = {e: float(np.mean([r6[j] for j, r in enumerate(recs) if r[1] == e])) for e in events}
        S[name] = dict(red=red, r6=r6, ev=ev, rot=np.array([res[(name, i)][1] for i in ids]),
                       npk=sum(res[(name, i)][2] for i in ids))
    out = dict(n_records=len(ids), n_events=len(events), events=events, dropped=list(drop_events), variants={})
    R = S['R']
    for name, s in S.items():
        dev = [s['ev'][e] - R['ev'][e] for e in events]
        o = dict(rec_mean=float(s['r6'].mean()), evt_mean=float(np.mean(list(s['ev'].values()))),
                 per_metric=s['red'].mean(0).tolist(), per_event=s['ev'], per_record=dict(zip(ids, s['r6'].tolist())),
                 rot_deg_mean=float(s['rot'].mean()), n_peak=int(s['npk']))
        if name != 'R':
            o.update(dS_evt=float(np.mean(dev)), dS_evt_ci95=boot_ci(dev), dS_rec=float(s['r6'].mean() - R['r6'].mean()),
                     n_events_better=int(sum(d > 0 for d in dev)), n_records_better=int((s['r6'] > R['r6']).sum()),
                     thmax_worse=int((s['red'][:, 4] < R['red'][:, 4]).sum()),
                     thmax_worst=float((s['red'][:, 4] - R['red'][:, 4]).min()),
                     thrms_worse=int((s['red'][:, 5] < R['red'][:, 5]).sum()),
                     thrms_worst=float((s['red'][:, 5] - R['red'][:, 5]).min()),
                     rot_change_pct=float((s['rot'].mean() / R['rot'].mean() - 1) * 100))
        if name == 'PEAK':
            fx = [S['PEAK']['ev'][e] - S['FIX45']['ev'][e] for e in events]
            o.update(dS_vs_FIX45_evt=float(np.mean(fx)), dS_vs_FIX45_ci95=boot_ci(fx))
            o['by_group'] = {}
            for gname in sorted({r[2] for r in recs}):
                j = [k for k, r in enumerate(recs) if r[2] == gname]
                o['by_group'][gname] = dict(n_records=len(j), dS_rec=float((s['r6'][j] - R['r6'][j]).mean()))
        out['variants'][name] = o
    return out


def verdict(o):
    """9주차 계획 4절의 판정 문장 (실행 전 고정)."""
    p = o['variants']['PEAK']; lo = p['dS_evt_ci95'][0]
    if p['dS_evt'] <= 0: v = '원문 15쌍의 개선은 새 지진에서 유지되지 않았다'
    elif lo > 0 and p['dS_vs_FIX45_evt'] > 0: v = '새 지진에서도 R보다 나았다'
    elif lo > 0: v = '개선은 피크 판단이 아니라 45° 쪽 운용에서 나온다'
    else: v = '개선 경향은 있지만 이 사건 수로는 확정할 수 없다'
    if p['dS_evt'] > 0 and p['dS_vs_FIX45_evt'] <= 0 and lo <= 0: v += ' (FIX45보다도 낫지 않음)'
    if p['thmax_worse'] > 0: v += ' / 비틀림 보호는 달성하지 못했다'
    return v


def table(o):
    print(f"{o['n_events']} events, {o['n_records']} records, dropped={o['dropped']}")
    print(f"{'variant':12s} {'rec%':>6s} {'evt%':>6s} {'dS_evt':>7s} {'95% CI':>16s} ev+ rec+ thmax- rot%")
    for name, v in o['variants'].items():
        if name == 'R':
            print(f"{name:12s} {v['rec_mean']:6.2f} {v['evt_mean']:6.2f}"); continue
        ci = v['dS_evt_ci95']
        print(f"{name:12s} {v['rec_mean']:6.2f} {v['evt_mean']:6.2f} {v['dS_evt']:+7.2f} [{ci[0]:+6.2f},{ci[1]:+6.2f}]"
              f" {v['n_events_better']:2d}/{o['n_events']} {v['n_records_better']:2d}/{o['n_records']}"
              f" {v['thmax_worse']:2d} {v['rot_change_pct']:+5.0f}")
    p = o['variants']['PEAK']
    print(f"PEAK - FIX45 (event): {p['dS_vs_FIX45_evt']:+.2f} {p['dS_vs_FIX45_ci95']}  groups: {p['by_group']}")
    print('판정:', verdict(o))


if __name__ == '__main__':
    name = sys.argv[1]; t0 = time.time()
    recs = record_list(name)
    jobs = [(v, r) for v in ['U', *VARIANTS] for r in recs]
    res = {}
    with ProcessPoolExecutor(max_workers=min(15, os.cpu_count())) as ex:
        for v, rid, m, rot, npk in ex.map(job, jobs):
            res[(v, rid)] = (m, rot, npk)
    print(f'{len(jobs)} runs, {time.time() - t0:.0f}s')
    if name == 'paper15':  # 회귀 확인
        uz = np.load(os.path.join(W8, 'reproduction_v2b', 'out_unc_zoh_up1.npy'))
        U = np.array([res[('U', r[0])][0] for r in recs])
        assert np.max(np.abs(U / uz - 1)) < 1e-6, np.max(np.abs(U / uz - 1))
    main = summarize(recs, res)
    if name == 'paper15':
        assert abs(main['variants']['R']['rec_mean'] - 15.811) < 0.01
        assert abs(main['variants']['PEAK']['dS_rec'] - 3.00) < 0.005
    out = dict(set=name, main=main, verdict=verdict(main))
    table(main)
    if any(r[1].startswith('Kocaeli') for r in recs):  # 9주차 계획 4절: Kocaeli 제외 결과 병기
        out['without_kocaeli'] = summarize(recs, res, drop_events=[e for e in {r[1] for r in recs} if e.startswith('Kocaeli')])
        out['verdict_without_kocaeli'] = verdict(out['without_kocaeli'])
        print(); table(out['without_kocaeli'])
    raw = {f'{v}|{rid}': list(val) for (v, rid), val in res.items()}
    json.dump(dict(out, raw=raw), open(os.path.join(pr.HERE, f'result_{name}.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)
