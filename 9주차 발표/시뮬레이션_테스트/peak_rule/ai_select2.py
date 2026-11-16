"""AI 선택기 v2: 학습 자료를 4사건에서 19사건으로 늘리고 선택지를 5개로 늘린다. 최종 평가는 test2에서 한 번만 한다.

v1(ai_select.py)은 4사건만으로 학습해 정확도 41%였다. test 세트(12사건)는 v1 PEAK 평가에 이미 한 번 썼다.
그래서 이제는 학습 자료로 쓸 수 있다. 이 AI의 독립 평가는 test2(9주차 계획 8절)에서 한다.

- 학습 자료: 원문 15쌍 + dev 18쌍 + test 25쌍 + 8주차 학습 사건 4쌍 = 62쌍, 19사건. 입력 회전 4각(0, 45, 90, 135°).
- T_OBS = 8 s까지는 모두 PEAK(당김 0.5). 그 뒤 선택지 5개 중 하나로 바꾼다:
  p0.5 (그대로), p0 (피크마다 45°), p1 (피크 방향 그대로), maxabs (r = max(|x|,|y|)), LP (v2 저역통과 판정)
- 특징 6개 (T_OBS까지 측정 가능한 값): log(RMS y/RMS x) 옥상, 45° 이탈(r² 가중), 비틀림 RMS/변위 RMS,
  log 최대 변위, log(RMS 지반가속도 y/x), 옥상 x 변위 영점 교차 진동수
- 모델: 선택지마다 (점수 − p0.5 점수)를 ridge 회귀로 예측한다. 예측이 가장 큰 선택지를 고른다(p0.5는 0).
- 검증: 사건 하나씩 빼기(19겹). 같은 기록의 회전 사례는 같은 겹에 둔다.
  비교 기준: 항상 p0.5, 학습 겹에서 고른 최선 고정값, 정답 선택.
- 채택 기준 (실행 전 고정): 원래 방향 사례의 사건 평균에서 AI − 최선 고정값 > 0이고, 개선 사건이 나빠진 사건보다 많을 것.
  채택되면 62쌍 전체로 다시 학습한 모델을 동결하고, test2의 비교군 AI로 넣는다.
"""
import os, json, time, pickle
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled, Peak
from peak_v2 import PeakV2

T_OBS = 8.0
ANG = np.deg2rad([0, 45, 90, 135])
ARMS = ['p0.5', 'p0', 'p1', 'maxabs', 'LP']
_plants = {}


class Switch(Peak):
    """T_OBS까지 PEAK(0.5). 그 뒤 arm으로 바꾼다. LP는 T_OBS부터 PeakV2 판정기로 넘긴다."""
    def __init__(s, dt, arm):
        super().__init__(dt); s.kT, s.arm = int(round(T_OBS / dt)), arm
        s.lp = PeakV2(dt, gap=0.0) if arm == 'LP' else None

    def decide(s, ob, hx, hy, th_act):
        k = ob.k
        if k == s.kT:
            if s.arm == 'p0': s.pull = 0.0
            elif s.arm == 'p1': s.pull = 1.0
            elif s.arm == 'maxabs': s.mag = 'maxabs'
        if s.lp is not None:
            o_lp = s.lp.decide(ob, hx, hy, th_act)  # 필터 상태를 처음부터 갱신
            if k >= s.kT:
                s.track(th_act); return o_lp
        return super().decide(ob, hx, hy, th_act)


def features(y, ax, ay, dt):
    k = int(round(T_OBS / dt)); x, yy, th = y[:k, 0], y[:k, 1], y[:k, 2]
    r2 = x ** 2 + yy ** 2
    dev45 = np.sum(r2 * np.abs(np.arctan2(np.abs(yy), np.abs(x)) - np.pi / 4)) / r2.sum()
    zc = np.sum(np.diff(np.sign(x)) != 0) / (2 * T_OBS)
    return [np.log(np.std(yy) / np.std(x)), dev45, np.std(th) / np.sqrt(r2.mean()), np.log(np.sqrt(r2.max())),
            np.log(np.std(ay[:k]) / np.std(ax[:k])), zc]


def rot(rec, a):
    ax, ay, dt = load(rec)
    return np.cos(a) * ax - np.sin(a) * ay, np.sin(a) * ax + np.cos(a) * ay, dt


def job(a):
    arm, rec, j, ia = a
    ax, ay, dt = rot(rec, ANG[ia])
    if arm == 'U': return a, uncontrolled(ax, ay, dt).tolist(), None
    if dt not in _plants: _plants[dt] = Plant(dt)
    if len(_plants[dt].cache) > 200: _plants[dt].cache.clear()
    y, _, _ = simulate(_plants[dt], ax, ay, Switch(dt, arm))
    return a, metrics(y).tolist(), features(y, ax, ay, dt)


def ridge(X, Y, lam=3.0):
    Xb = np.c_[X, np.ones(len(X))]; R = lam * np.eye(Xb.shape[1]); R[-1, -1] = 0
    return np.linalg.solve(Xb.T @ Xb + R, Xb.T @ Y)


def fit(X, D):
    mu, sd = X.mean(0), X.std(0) + 1e-12
    return mu, sd, ridge((X - mu) / sd, D)


def predict(model, X):
    mu, sd, W = model
    P = np.c_[(X - mu) / sd, np.ones(len(X))] @ W
    return np.argmax(np.c_[np.zeros(len(X)), P], 1)  # 0 = p0.5


if __name__ == '__main__':
    t0 = time.time()
    recs = rs.record_list('paper15') + rs.record_list('dev') + rs.record_list('test') + rs.record_list('week8')
    ev = lambda r: r[1].replace(',', '').split()[0]
    jobs = [(arm, rec, j, ia) for arm in ['U'] + ARMS for j, rec in enumerate(recs) for ia in range(len(ANG))]
    res = {}
    with ProcessPoolExecutor(max_workers=12) as ex:
        for a, m, f in ex.map(job, jobs, chunksize=2):
            res[(a[0], a[2], a[3])] = (np.array(m), f)
            if len(res) % 100 == 0: print(f'{len(res)}/{len(jobs)} {time.time() - t0:.0f}s', flush=True)
    case = [(j, ia) for j in range(len(recs)) for ia in range(len(ANG))]
    sc = lambda arm, j, ia: float(((1 - res[(arm, j, ia)][0] / res[('U', j, ia)][0]) * 100).mean())
    S = np.array([[sc(arm, *c) for arm in ARMS] for c in case])  # 사례 × 선택지
    X = np.array([res[('p0.5', *c)][1] for c in case]); E = np.array([ev(recs[j]) for j, _ in case])
    for arm in ARMS[1:]: assert np.allclose(X, [res[(arm, *c)][1] for c in case]), arm  # 인과성
    D = S[:, 1:] - S[:, :1]; evs = sorted(set(E))
    pick = np.zeros(len(case), int); const = np.zeros(len(case), int)
    for e in evs:
        tr, te = E != e, E == e
        pick[te] = predict(fit(X[tr], D[tr]), X[te])
        const[te] = int(np.argmax(S[tr].mean(0)))
    idx = np.arange(len(case))
    sel = dict(p05=S[:, 0], const=S[idx, const], AI=S[idx, pick], oracle=S.max(1))
    for i, arm in enumerate(ARMS[1:], 1): sel['always_' + arm] = S[:, i]
    evt_vec = lambda s, m: np.array([s[m & (E == e)].mean() for e in evs])
    out = dict(T_OBS=T_OBS, n_case=len(case), n_event=len(evs), arms=ARMS, rows={},
               pick_counts={a: int((pick == i).sum()) for i, a in enumerate(ARMS)},
               const_counts={a: int((const == i).sum()) for i, a in enumerate(ARMS)})
    print(f'{len(jobs)} runs {time.time() - t0:.0f}s, {len(evs)} events')
    for name, m in [('all rotations', np.ones(len(case), bool)), ('unrotated', np.array([ia == 0 for _, ia in case]))]:
        base = evt_vec(sel['p05'], m)
        row = {k: float((evt_vec(v, m) - base).mean()) for k, v in sel.items()}
        dc = evt_vec(sel['AI'], m) - evt_vec(sel['const'], m)
        row['AI_vs_const_better_events'] = int((dc > 1e-9).sum()); row['AI_vs_const_worse_events'] = int((dc < -1e-9).sum())
        out['rows'][name] = row
        print(f'{name:14s} 사건 평균, p0.5 대비 %p: ' + '  '.join(f'{k} {v:+.2f}' if isinstance(v, float) else f'{k} {v}' for k, v in row.items()))
    print('AI 선택 횟수', out['pick_counts'], ' 고정값 선택', out['const_counts'])
    u = out['rows']['unrotated']
    adopt = (u['AI'] - u['const'] > 0) and u['AI_vs_const_better_events'] > u['AI_vs_const_worse_events']
    out['adopt'] = bool(adopt); print('채택:', adopt)
    if adopt:
        pickle.dump(fit(X, D), open(os.path.join(rs.pr.HERE, 'ai_select2_model.pkl'), 'wb'))
    json.dump(out, open(os.path.join(rs.pr.HERE, 'result_ai_select2.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    np.savez(os.path.join(rs.pr.HERE, 'ai_select2_cases.npz'), S=S, X=X, E=E, pick=pick, const=const)
