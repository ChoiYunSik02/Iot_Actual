"""밸브 채널의 물리적 상한 (개발 실험, 62쌍). test2는 쓰지 않는다.

AI를 밸브 제어에 쓸 가치가 있는지 먼저 잰다. LP_V의 회전판·펌프 궤적을 고정하고, 지진 전체를 미리 안다고 가정해
매 스텝 밸브 감쇠 c(k)를 연속값(kappa 0.1~0.8 범위)으로 경사 최적화한다. 미래를 쓰므로 실현 불가능한 상한이다.
목적함수는 6지표(무제어 대비) 평균. 시뮬레이션은 sim_layer.simulate와 같은 이산 행렬·밸브 식을 torch로 옮겼고,
최적화 전 값이 simulate의 LP_V와 일치하는지 assert로 확인한다.
"""
import os, sys, json, time
import numpy as np
import torch
from concurrent.futures import ProcessPoolExecutor, as_completed
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled
from run_test2 import POL
from rs_ref import cdamp
from tlcd3 import IDX, N

ITERS = 200
n_ = 3 * N + 2
K = np.linspace(0.1, 0.8, 71)
_plants = {}


def forward(Ad, Bd, idx, ax, ay, c, x0):
    i = IDX; ivr = [(n_ + i['xd'], n_ + i['xt']), (n_ + i['yd'], n_ + i['yt'])]; out = [i['xt'], i['yt'], i['tt']]
    x = x0; ys = []
    for k in range(len(ax)):
        ys.append(x[out])
        vr = torch.stack([x[a] - x[b] for a, b in ivr])
        u = torch.cat([ax[k:k + 1], ay[k:k + 1], c[k] * vr.abs() * vr])
        x = Ad[idx[k]] @ x + Bd[idx[k]] @ u
    return torch.stack(ys)


def met(y):
    s = torch.tensor([100., 100, 1e4], dtype=y.dtype); a = y.abs() * s; r = (y ** 2).mean(0).sqrt() * s
    return torch.stack([a[:, 0].max(0)[0], r[0], a[:, 1].max(0)[0], r[1], a[:, 2].max(0)[0], r[2]])


def job(a):
    torch.set_num_threads(1)
    j, rec = a; t0 = time.time()
    ax, ay, dt = load(rec)
    if dt not in _plants: _plants[dt] = Plant(dt)
    p = _plants[dt]; p.cache.clear()
    y0, _, st = simulate(p, ax, ay, POL['LP_V'](dt)); m0 = metrics(y0); U = uncontrolled(ax, ay, dt)
    keys, idx, D = {}, [], []
    for s in st:
        key = (s[4], round(float(np.deg2rad(s[3])), 4))
        if key not in keys: keys[key] = len(D); D.append(p.disc(*key))
        idx.append(keys[key])
    Ad = torch.tensor(np.array([d[0] for d in D])); Bd = torch.tensor(np.array([d[1] for d in D]))
    del D; p.cache.clear()  # 이 기록에 필요한 행렬은 Ad, Bd에 있으므로 캐시를 비운다
    AX, AY = torch.tensor(ax), torch.tensor(ay); x0 = torch.zeros(2 * n_, dtype=torch.float64); Ut = torch.tensor(U)
    cs = np.array([cdamp(q) for q in K]); cmin, cmax = cs.min(), cs.max()
    c0 = np.array([cdamp(s[5]) for s in st])
    with torch.no_grad():
        m_chk = met(forward(Ad, Bd, idx, AX, AY, torch.tensor(c0), x0)).numpy()
    assert np.abs(m_chk / m0 - 1).max() < 1e-3, (rec[0], m_chk, m0)
    q = np.clip((c0 - cmin) / (cmax - cmin), 0.02, 0.98)
    z = torch.tensor(np.log(q / (1 - q)), requires_grad=True); opt = torch.optim.Adam([z], lr=0.15)
    best = (np.inf, None); iters = int(os.environ.get('ITERS', ITERS))
    for it in range(iters):
        c = cmin + (cmax - cmin) * torch.sigmoid(z)
        m = met(forward(Ad, Bd, idx, AX, AY, c, x0)); L = (m / Ut).mean()
        if L.item() < best[0]: best = (L.item(), m.detach().numpy().copy())
        opt.zero_grad(); L.backward(); opt.step(); del m, L, c
    return j, U.tolist(), m0.tolist(), best[1].tolist(), len(ax), time.time() - t0


if __name__ == '__main__':
    recs = sum((rs.record_list(s) for s in ('paper15', 'dev', 'test', 'week8')), [])
    assert not ({r[0] for r in recs} & {r[0] for r in rs.record_list('test2')})
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else len(recs)
    order = sorted(range(len(recs)), key=lambda j: os.path.getsize(recs[j][3]))[:lim]
    t0 = time.time(); R = {}
    CK = 'valve_oracle_ckpt.jsonl'  # 기록별 중간 저장: 끊겨도 끝난 기록은 다시 계산하지 않는다
    if os.path.exists(CK):
        for line in open(CK, encoding='utf-8'):
            j, U, m0, mo = json.loads(line); R[j] = (np.array(U), np.array(m0), np.array(mo))
        print(f'checkpoint {len(R)} records', flush=True)
    with ProcessPoolExecutor(max_workers=int(os.environ.get('WORKERS', 8))) as ex:
        for fu in as_completed([ex.submit(job, (j, recs[j])) for j in order if j not in R]):
            j, U, m0, mo, T, s = fu.result()
            R[j] = (np.array(U), np.array(m0), np.array(mo))
            with open(CK, 'a', encoding='utf-8') as fh: fh.write(json.dumps([j, U, m0, mo]) + '\n')
            g = ((1 - R[j][2] / R[j][0]) - (1 - R[j][1] / R[j][0])).mean() * 100
            print(f'{recs[j][0]} {recs[j][1]} T={T} {s:.0f}s gain {g:+.2f}', flush=True)
    ev = lambda r: r[1].replace(',', '').split()[0]; use = sorted(R); evs = sorted({ev(recs[j]) for j in use})
    d = {j: ((R[j][1] - R[j][2]) / R[j][0]).mean() * 100 for j in use}
    de = [np.mean([d[j] for j in use if ev(recs[j]) == e]) for e in evs]
    base = {j: (1 - R[j][1] / R[j][0]).mean() * 100 for j in use}
    out = dict(n_pairs=len(use), n_events=len(evs), LP_V_rec=float(np.mean(list(base.values()))),
               oracle_minus_LP_V_evt=float(np.mean(de)), ci95=rs.boot_ci(de), per_event=dict(zip(evs, map(float, de))))
    print(json.dumps(out, ensure_ascii=False, indent=1), f'{time.time() - t0:.0f}s')
    if lim == len(recs): json.dump(out, open('result_valve_oracle.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
