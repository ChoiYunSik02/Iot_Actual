"""10주차 B0': 밸브 상한 해 c*(k) 궤적 저장 (계획 12절). 9주차 valve_oracle.py와 같은 설정(200회, Adam 0.15)이고,
기록별 최적 감쇠 궤적을 results_valve_oracle/rec_XX.npz로 남기는 것만 다르다. 개발 62쌍, test2는 쓰지 않는다.
끝난 기록은 건너뛴다. 끝나면 상한 값을 9주차(+3.24%p)와 대조하고 요약을 커밋·알림한다.
"""
import os, sys, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '9주차 발표', '시뮬레이션_테스트', 'peak_rule'))
import torch  # noqa: E402
import run_set as rs  # noqa: E402
from run_set import Plant, simulate, metrics, load, uncontrolled  # noqa: E402
from run_test2 import POL  # noqa: E402
from rs_ref import cdamp  # noqa: E402
from valve_oracle import forward, met, K, n_, ITERS  # noqa: E402
from ground_ai import log, notify, git_commit, low_priority, REPO  # noqa: E402

OUT = os.environ.get('ORACLE_OUT', os.path.join(HERE, 'results_valve_oracle'))
ITERS = int(os.environ.get('ITERS', ITERS))  # 시험용 덮어쓰기. 본 실행은 200


def job(a):
    """valve_oracle.job과 같은 계산. 최선 손실일 때의 c(k)를 함께 돌려준다."""
    torch.set_num_threads(1); low_priority()
    j, rec = a; t0 = time.time()
    ax, ay, dt = load(rec); p = Plant(dt)
    y0, _, st = simulate(p, ax, ay, POL['LP_V'](dt)); m0 = metrics(y0); U = uncontrolled(ax, ay, dt)
    keys, idx, D = {}, [], []
    for s in st:
        key = (s[4], round(float(np.deg2rad(s[3])), 4))
        if key not in keys: keys[key] = len(D); D.append(p.disc(*key))
        idx.append(keys[key])
    Ad = torch.tensor(np.array([d[0] for d in D])); Bd = torch.tensor(np.array([d[1] for d in D])); del D
    AX, AY = torch.tensor(ax), torch.tensor(ay); x0 = torch.zeros(2 * n_, dtype=torch.float64); Ut = torch.tensor(U)
    cs = np.array([cdamp(q) for q in K]); cmin, cmax = cs.min(), cs.max()
    c0 = np.array([cdamp(s[5]) for s in st])
    with torch.no_grad():
        m_chk = met(forward(Ad, Bd, idx, AX, AY, torch.tensor(c0), x0)).numpy()
    assert np.abs(m_chk / m0 - 1).max() < 1e-3, (rec[0], m_chk, m0)
    q = np.clip((c0 - cmin) / (cmax - cmin), 0.02, 0.98)
    z = torch.tensor(np.log(q / (1 - q)), requires_grad=True); opt = torch.optim.Adam([z], lr=0.15)
    best = (np.inf, None, None)
    for _ in range(ITERS):
        c = cmin + (cmax - cmin) * torch.sigmoid(z)
        m = met(forward(Ad, Bd, idx, AX, AY, c, x0)); L = (m / Ut).mean()
        if L.item() < best[0]: best = (L.item(), m.detach().numpy().copy(), c.detach().numpy().copy())
        opt.zero_grad(); L.backward(); opt.step(); del m, L, c
    np.savez(os.path.join(OUT, f'rec_{j:02d}.npz'), c_best=best[2].astype(np.float32), c_rule=c0.astype(np.float32),
             m0=m0, m_best=best[1], U=U, dt=dt, rec_id=rec[0], event=rec[1])
    return j, rec[0], len(ax), time.time() - t0


def main():
    low_priority(); os.makedirs(OUT, exist_ok=True); logp = os.path.join(OUT, 'run.log'); done = os.path.join(OUT, 'DONE')
    if os.path.exists(done): log('이미 완료됨, 종료', logp); return
    recs = sum((rs.record_list(s) for s in ('paper15', 'dev', 'test', 'week8')), [])
    assert not ({r[0] for r in recs} & {r[0] for r in rs.record_list('test2')})
    todo = [j for j in range(len(recs)) if not os.path.exists(os.path.join(OUT, f'rec_{j:02d}.npz'))]
    t0 = time.time(); log(f'시작: 남은 기록 {len(todo)}/{len(recs)}', logp)
    try:
        with ProcessPoolExecutor(max_workers=int(os.environ.get('WORKERS', 12))) as ex:
            for fu in as_completed([ex.submit(job, (j, recs[j])) for j in todo]):
                j, rid, T, s = fu.result(); log(f'{rid} T={T} {s:.0f}s', logp)
        ev = lambda r: r[1].replace(',', '').split()[0]; evs = sorted({ev(r) for r in recs})
        R = [np.load(os.path.join(OUT, f'rec_{j:02d}.npz')) for j in range(len(recs))]
        d = [float(((r['m0'] - r['m_best']) / r['U']).mean() * 100) for r in R]
        de = np.array([np.mean([d[j] for j in range(len(recs)) if ev(recs[j]) == e]) for e in evs])
        w9 = json.load(open(os.path.join(REPO, '9주차 발표', '시뮬레이션_테스트', 'peak_rule', 'result_valve_oracle.json'), encoding='utf-8'))
        out = dict(n_pairs=len(recs), n_events=len(evs), oracle_minus_LP_V_evt=float(de.mean()), ci95=rs.boot_ci(de),
                   week9_value=w9['oracle_minus_LP_V_evt'], match_week9=bool(abs(de.mean() - w9['oracle_minus_LP_V_evt']) < 0.05),
                   per_event=dict(zip(evs, map(float, de))), minutes=(time.time() - t0) / 60)
        json.dump(out, open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        open(done, 'w').write(time.strftime('%Y-%m-%d %H:%M:%S')); log(f'완료: 상한 {de.mean():+.2f}%p (9주차 {w9["oracle_minus_LP_V_evt"]:+.2f})', logp)
        rel = os.path.relpath(OUT, REPO)
        git_commit([os.path.join(rel, n) for n in ('summary.json', 'run.log', 'DONE')],
                   f'10주차 B0\': 밸브 상한 궤적 저장 완료 (상한 {de.mean():+.2f}%p, 9주차와 {"일치" if out["match_week9"] else "불일치"})', logp)
        notify(f'밸브 상한 재계산 완료: {de.mean():+.2f}%p (9주차 {w9["oracle_minus_LP_V_evt"]:+.2f}). 궤적 저장됨', logp)
    except Exception as e:
        import traceback; log('오류: ' + traceback.format_exc(), logp)
        notify(f'밸브 상한 재계산 오류: {type(e).__name__}. 다음 예약 시각에 이어서 재시도', logp); raise


if __name__ == '__main__':
    main()
