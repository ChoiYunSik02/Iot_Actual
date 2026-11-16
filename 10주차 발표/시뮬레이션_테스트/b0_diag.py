"""10주차 B0: 9주차 NN_V가 학습되지 않은 원인 진단 (학습 없음, 계획 12절). 개발 62쌍, test2 안 씀.

  python b0_diag.py ab [--smoke]   (a) LP_V에서 원문 밸브 규칙이 끝값(κ=0.1, 0.8)을 고른 스텝 비율
                                   (b) 9주차 NN_V 설정(출력 0 초기값, 앞 40 s 역전파)의 기록별 기울기 노름과
                                       기록 사이 기울기 방향 일치도(코사인), 전체 평균 기울기 노름
  python b0_diag.py c  [--smoke]   (c) 밸브 상한 해 log c*(k)를 현재 측정값 13개로 선형 회귀한 R² (사건 빼기).
                                       B0'(results_valve_oracle/rec_XX.npz)이 끝난 뒤 실행한다.
"""
import os, sys, json, time, argparse
import numpy as np
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'results_b0')
os.environ.setdefault('NN_CACHE', os.path.join(OUT, 'nn_cache'))
sys.path.insert(0, os.path.join(HERE, '..', '..', '9주차 발표', '시뮬레이션_테스트', 'peak_rule'))
import torch  # noqa: E402
import run_set as rs  # noqa: E402
from run_set import Plant, simulate, load  # noqa: E402
from run_test2 import POL  # noqa: E402
import valve_nn as vn  # noqa: E402
from ground_ai import low_priority, log  # noqa: E402

ORACLE = os.environ.get('ORACLE_OUT', os.path.join(HERE, 'results_valve_oracle'))


def recs62():
    return sum((rs.record_list(s) for s in ('paper15', 'dev', 'test', 'week8')), [])


def job_a(a):
    """LP_V 궤적에서 밸브 κ 분포. st[5]가 매 스텝 κ (nc=1)."""
    low_priority(); j, rec = a; ax, ay, dt = load(rec)
    _, _, st = simulate(Plant(dt), ax, ay, POL['LP_V'](dt))
    kap = np.array([s[5] for s in st])
    return j, {str(k): float(np.mean(np.isclose(kap, k))) for k in (0.1, 0.4, 0.8)}


def job_b(j):
    low_priority(); torch.set_num_threads(1)
    m = vn.net(); sd = {k: v.clone() for k, v in m.state_dict().items()}
    L, g = vn.grad((j, sd))
    return j, L, np.concatenate([x.ravel() for x in g])


def part_ab(recs, logp, smoke):
    os.makedirs(os.environ['NN_CACHE'], exist_ok=True)
    idx = list(range(len(recs)))
    if smoke: idx = sorted(idx, key=lambda j: os.path.getsize(recs[j][3]))[:2]
    with ProcessPoolExecutor(max_workers=int(os.environ.get('WORKERS', 12))) as ex:
        A = dict(ex.map(job_a, [(j, recs[j]) for j in idx])); log('(a) 끝', logp)
        list(ex.map(vn.build, [(j, recs[j]) for j in idx if not os.path.exists(os.path.join(os.environ['NN_CACHE'], f'{j}.npz'))]))
        B = {j: (L, g) for j, L, g in ex.map(job_b, idx)}; log('(b) 끝', logp)
    ev = vn.EV; evs = sorted({ev(recs[j]) for j in idx}); cnt = {e: sum(ev(recs[j]) == e for j in idx) for e in evs}
    G = np.array([B[j][1] for j in idx]); w = np.array([1 / cnt[ev(recs[j])] for j in idx]); w /= w.sum()
    gbar = (w[:, None] * G).sum(0); norms = np.linalg.norm(G, axis=1)
    U = G / (norms[:, None] + 1e-30); cos = U @ U.T; off = cos[~np.eye(len(idx), dtype=bool)]
    end = np.array([A[j]['0.1'] + A[j]['0.8'] for j in idx])
    out = dict(n_pairs=len(idx),
               a_end_share_mean=float(end.mean()), a_end_share_min=float(end.min()), a_end_share_max=float(end.max()),
               a_share_by_kappa={k: float(np.mean([A[j][k] for j in idx])) for k in ('0.1', '0.4', '0.8')},
               b_grad_norm_per_record_median=float(np.median(norms)), b_grad_norm_per_record_max=float(norms.max()),
               b_share_records_over_clip1=float(np.mean(norms > 1.0)), b_full_batch_grad_norm=float(np.linalg.norm(gbar)),
               b_full_over_mean_record=float(np.linalg.norm(gbar) / np.average(norms, weights=w)),
               b_cos_median=float(np.median(off)), b_cos_share_negative=float(np.mean(off < 0)),
               b_loss_mean=float(np.mean([B[j][0] for j in idx])))
    return out


def feats_along(rec_npz, rec):
    """상한 해 c*로 다시 돌린 상태에서 9주차 Mem 특징 13개를 매 스텝 계산한다(인과)."""
    ax, ay, dt = load(rec); p = Plant(dt)
    _, _, st = simulate(p, ax, ay, POL['LP_V'](dt))
    keys, idx, D = {}, [], []
    for s in st:
        key = (s[4], round(float(np.deg2rad(s[3])), 4))
        if key not in keys: keys[key] = len(D); D.append(p.disc(*key))
        idx.append(keys[key])
    th = np.deg2rad([s[2] for s in st]); c = rec_npz['c_best'].astype(float)
    x = np.zeros(2 * vn.n_); vp = np.zeros(2); mem = vn.Mem(dt); F = []
    with torch.no_grad():
        for k in range(len(ax)):
            vt = x[vn.IT]; vr = x[vn.IV] - vt; aa = ((vt - vp) / dt if k else np.zeros(2)) + np.array([ax[k], ay[k]]); vp = vt.copy()
            F.append(mem.feat(torch.tensor(vr), torch.tensor(aa), torch.tensor(float(th[k]))).numpy())
            Ad, Bd = D[idx[k]]; x = Ad @ x + Bd @ np.r_[ax[k], ay[k], c[k] * np.abs(vr) * vr]
    return np.array(F), np.log(c), dt


def job_c(a):
    low_priority(); torch.set_num_threads(1); j, rec = a
    z = np.load(os.path.join(ORACLE, f'rec_{j:02d}.npz')); F, y, dt = feats_along(z, rec)
    s = max(1, int(round(0.05 / dt)))
    return j, F[1::s], y[1::s]


def part_c(recs, logp, smoke):
    idx = [j for j in range(len(recs)) if os.path.exists(os.path.join(ORACLE, f'rec_{j:02d}.npz'))]
    if smoke: idx = idx[:3]
    assert idx, 'B0\' 결과(results_valve_oracle/rec_XX.npz)가 없다'
    with ProcessPoolExecutor(max_workers=int(os.environ.get('WORKERS', 12))) as ex:
        D = {j: (F, y) for j, F, y in ex.map(job_c, [(j, recs[j]) for j in idx])}
    ev = vn.EV; evs = sorted({ev(recs[j]) for j in idx}); r2 = {}
    for e in evs:
        tr = [j for j in idx if ev(recs[j]) != e]; te = [j for j in idx if ev(recs[j]) == e]
        if not tr: continue
        X = np.vstack([D[j][0] for j in tr]); Y = np.concatenate([D[j][1] for j in tr])
        A = np.c_[X, np.ones(len(X))]; w = np.linalg.solve(A.T @ A + 1e-3 * np.eye(A.shape[1]), A.T @ Y)
        Xt = np.vstack([D[j][0] for j in te]); Yt = np.concatenate([D[j][1] for j in te])
        r2[e] = float(1 - np.mean((Yt - np.c_[Xt, np.ones(len(Xt))] @ w) ** 2) / np.var(Yt))
    Yb = np.concatenate([np.log(np.load(os.path.join(ORACLE, f'rec_{j:02d}.npz'))['c_best'].astype(float)) for j in idx])
    Yr = np.concatenate([np.log(np.load(os.path.join(ORACLE, f'rec_{j:02d}.npz'))['c_rule'].astype(float)) for j in idx])
    return dict(n_pairs=len(idx), c_r2_event_mean=float(np.mean(list(r2.values()))), c_r2_per_event=r2,
                rule_r2=float(1 - np.mean((Yb - Yr) ** 2) / np.var(Yb)))  # 원문 규칙 자체가 c*를 얼마나 설명하나 (모든 스텝)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('part', choices=['ab', 'c']); ap.add_argument('--smoke', action='store_true'); A = ap.parse_args()
    low_priority(); os.makedirs(OUT, exist_ok=True); logp = os.path.join(OUT, 'run.log'); t0 = time.time()
    recs = recs62(); assert not ({r[0] for r in recs} & {r[0] for r in rs.record_list('test2')})
    log(f'시작 {A.part}' + (' (smoke)' if A.smoke else ''), logp)
    out = part_ab(recs, logp, A.smoke) if A.part == 'ab' else part_c(recs, logp, A.smoke)
    out['minutes'] = (time.time() - t0) / 60
    fn = os.path.join(OUT, f'result_b0_{A.part}' + ('_smoke' if A.smoke else '') + '.json')
    json.dump(out, open(fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('완료 ' + json.dumps({k: v for k, v in out.items() if not isinstance(v, dict)}, ensure_ascii=False), logp)


if __name__ == '__main__':
    main()
