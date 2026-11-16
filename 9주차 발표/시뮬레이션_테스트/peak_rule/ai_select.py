"""AI 선택기: 처음 T_OBS 초 옥상 응답을 보고 피크 규칙의 당김 비율(0.5 또는 1)을 고른다. dev 기록만 쓴다. test 세트는 쓰지 않는다.

상한 (result_paper15/dev.json에서 계산): 기록마다 최선 변형을 고르면 PEAK 대비 +1.00 / +1.37%p, 대부분 당김 0.5 vs 1 선택에서 나온다.

- 사례: 원문 15쌍 + dev 18쌍(4사건) × 입력 회전 8각(0~157.5°) = 264개. 회전은 학습 사례를 늘리려는 것이다.
- 두 정책: A = PEAK(pull 0.5) 끝까지. B = T_OBS까지 A와 같고, 그 뒤 pull 1. T_OBS 전 응답은 A와 B가 같으므로 특징이 같다.
- 특징 (T_OBS까지 옥상 X·Y 변위와 비틀림각, 제어기가 실제로 볼 수 있는 값만):
  log(RMS y / RMS x), 변위 방향의 45°에서 벗어난 정도(r² 가중), 비틀림 RMS / 변위 RMS, log 최대 변위
- 모델: 로지스틱 회귀 (numpy, L2). 라벨 = B가 A보다 나으면 1.
- 검증: 사건 하나씩 빼기 (4겹). 같은 기록의 회전 사례는 같은 겹에 둔다.
  비교 기준: 항상 A, 항상 B, 학습 겹에서 고른 최선 고정값, 정답 선택(상한).
T_OBS = 10 s, 회전 8각, 특징 4개는 실행 전에 정했다.
"""
import os, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled, Peak

T_OBS = 10.0
ANG = np.deg2rad(np.arange(8) * 22.5)
_plants = {}


class Switch(Peak):
    def __init__(s, dt, pull_after):
        super().__init__(dt); s.kT, s.pa = int(round(T_OBS / dt)), pull_after

    def decide(s, ob, hx, hy, th_act):
        if ob.k == s.kT: s.pull = s.pa
        return super().decide(ob, hx, hy, th_act)


def rot(rec, a):
    ax, ay, dt = load(rec)
    return np.cos(a) * ax - np.sin(a) * ay, np.sin(a) * ax + np.cos(a) * ay, dt


def features(y, dt):
    k = int(round(T_OBS / dt)); x, yy, th = y[:k, 0], y[:k, 1], y[:k, 2]
    r2 = x ** 2 + yy ** 2
    dev45 = np.sum(r2 * np.abs(np.arctan2(np.abs(yy), np.abs(x)) - np.pi / 4)) / r2.sum()
    return [np.log(np.std(yy) / np.std(x)), dev45, np.std(th) / np.sqrt(r2.mean()), np.log(np.sqrt(r2.max()))]


def job(a):
    kind, rec, j, ia = a
    ax, ay, dt = rot(rec, ANG[ia])
    if kind == 'U': return a, uncontrolled(ax, ay, dt).tolist(), None
    if dt not in _plants: _plants[dt] = Plant(dt)
    if len(_plants[dt].cache) > 200: _plants[dt].cache.clear()
    y, _, _ = simulate(_plants[dt], ax, ay, Switch(dt, 0.5 if kind == 'A' else 1.0))
    return a, metrics(y).tolist(), features(y, dt)


def logreg(X, t, lam=1.0, it=3000, lr=0.1):
    w = np.zeros(X.shape[1] + 1); Xb = np.c_[X, np.ones(len(X))]
    for _ in range(it):
        p = 1 / (1 + np.exp(-Xb @ w)); g = Xb.T @ (p - t) / len(t); g[:-1] += lam * w[:-1] / len(t); w -= lr * g
    return w


if __name__ == '__main__':
    t0 = time.time()
    recs = rs.record_list('paper15') + rs.record_list('dev')
    ev = lambda r: r[1].replace(',', '').split()[0]
    jobs = [(k, rec, j, ia) for k in 'UAB' for j, rec in enumerate(recs) for ia in range(len(ANG))]
    res = {}
    with ProcessPoolExecutor(max_workers=12) as ex:
        for a, m, f in ex.map(job, jobs, chunksize=2):
            res[(a[0], a[2], a[3])] = (np.array(m), f)
            if len(res) % 100 == 0: print(f'{len(res)}/{len(jobs)} {time.time() - t0:.0f}s', flush=True)
    case = [(j, ia) for j in range(len(recs)) for ia in range(len(ANG))]
    sc = lambda k, j, ia: float(((1 - res[(k, j, ia)][0] / res[('U', j, ia)][0]) * 100).mean())
    SA = np.array([sc('A', *c) for c in case]); SB = np.array([sc('B', *c) for c in case])
    X = np.array([res[('A', *c)][1] for c in case]); E = np.array([ev(recs[j]) for j, _ in case])
    # A와 B의 T_OBS 이전 특징이 같은지 확인 (인과성)
    assert np.allclose(X, np.array([res[('B', *c)][1] for c in case]))
    t = (SB > SA).astype(float); evs = sorted(set(E)); pick = np.zeros(len(case)); const = np.zeros(len(case))
    for e in evs:
        tr, te = E != e, E == e
        mu, sd = X[tr].mean(0), X[tr].std(0)
        w = logreg((X[tr] - mu) / sd, t[tr])
        pick[te] = (np.c_[(X[te] - mu) / sd, np.ones(te.sum())] @ w) > 0
        const[te] = SB[tr].mean() > SA[tr].mean()  # 학습 겹에서 고른 최선 고정값
    S = dict(A=SA, B=SB, const=np.where(const, SB, SA), AI=np.where(pick, SB, SA), oracle=np.maximum(SA, SB))
    evt = lambda s, m: float(np.mean([s[m & (E == e)].mean() for e in evs]))
    out = {'T_OBS': T_OBS, 'n_case': len(case), 'label_B_better': float(t.mean()), 'ai_acc': float((pick == t).mean()), 'rows': {}}
    print(f'{len(jobs)} runs {time.time() - t0:.0f}s  B better in {t.mean():.0%} of cases, AI accuracy (LOEO) {(pick == t).mean():.0%}')
    for name, m in [('all rotations', np.ones(len(case), bool)), ('unrotated (원래 방향)', np.array([ia == 0 for _, ia in case]))]:
        row = {k: evt(v, m) - evt(SA, m) for k, v in S.items()}; out['rows'][name] = row
        print(f'{name:22s} 사건 평균, 항상 A 대비 %p: ' + '  '.join(f'{k} {v:+.2f}' for k, v in row.items()))
    for e in evs:
        m = E == e; print(f'  {e:10s} AI-A {S["AI"][m].mean() - SA[m].mean():+.2f}  oracle-A {S["oracle"][m].mean() - SA[m].mean():+.2f}  B-A {SB[m].mean() - SA[m].mean():+.2f}')
    json.dump(out, open(os.path.join(rs.pr.HERE, 'result_ai_select.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    np.savez(os.path.join(rs.pr.HERE, 'ai_select_cases.npz'), SA=SA, SB=SB, X=X, E=E, pick=pick)
