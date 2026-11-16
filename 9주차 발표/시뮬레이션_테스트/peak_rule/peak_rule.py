"""피크 기반 회전판 규칙 재구현 (8주차 v19 발표 설명만으로 작성, 원본 코드 ai_improvement_v4 미확보).

규칙 (v19 4쪽·부록 17~18쪽):
  1. 매 스텝 옥상 X·Y 변위 크기 r(k)를 잰다.
  2. r(k-1) > r(k-2) 이고 r(k) < r(k-1) 이면 k-1을 피크로 판정 (현재까지 측정값만 사용).
  3. r(k-1) >= 0.3 × (지금까지 최대 r) 인 피크만 사용.
  4. 피크 순간 방향 φ = atan2(|y|, |x|)를 45° 쪽으로 절반 당긴 θ* = 45° + 0.5(φ − 45°)를 회전판 목표각으로.
  5. 회전 속도 30°/s (Actuator), 펌프는 원문 2.6 s 규칙, 밸브는 원문 1 s 규칙 (해석 A) 그대로.

발표 설명으로 정해지지 않는 부분(r의 정의, 당김 비율)은 변형으로 함께 돌려 v19 수치와 대조한다.
모델: 8주차 재현 모델 D0·A (reproduction_v2b/sim_layer.py, 지연 0에서 rs_ref.run과 일치 확인됨).
"""
import sys, os, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
W8 = os.path.join(HERE, '..', '..', '..', '8주차 발표', '시뮬레이션_테스트')
sys.path[:0] = [os.path.join(W8, 'reproduction_v2b'), os.path.join(W8, 'reproduction_v2')]

from rs_ref import Plant  # noqa: E402
from sim_layer import simulate, RPolicy  # noqa: E402
from tlcd import load_records, metrics  # noqa: E402

EVENT = ['IV'] * 12 + ['NR', 'KB', 'CC']  # records_table2.csv 순서
V19 = dict(rec_gain=3.00, evt_gain=2.40, n_better=14, rot_change=-17.0)  # v19 발표 수치 (R 대비)


class Tracked(RPolicy):
    """원문 R. 회전판 실제 누적 회전량을 기록한다."""
    def __init__(s, dt):
        super().__init__(dt, 'A'); s.rot = 0.0; s.th_last = 0.0

    def track(s, th_act):
        s.rot += abs(th_act - s.th_last); s.th_last = th_act

    def decide(s, ob, hx, hy, th_act):
        s.track(th_act)
        return super().decide(ob, hx, hy, th_act)


class Peak(Tracked):
    def __init__(s, dt, mag='norm', frac=0.3, pull=0.5):
        super().__init__(dt); s.mag, s.frac, s.pull = mag, frac, pull
        s.r1 = s.r2 = s.rmax = 0.0; s.n_peak = 0

    def decide(s, ob, hx, hy, th_act):
        s.track(th_act); k = ob.k
        # 펌프(진동수)는 원문 2.6 s 규칙 그대로, 원문의 각도 지령만 버린다
        out = [(kind, {'f': cmd['f']}, rec) for kind, cmd, rec in RPolicy.decide(s, ob, hx, hy, th_act)]
        r = np.hypot(hx[k], hy[k]) if s.mag == 'norm' else max(abs(hx[k]), abs(hy[k]))
        if k >= 2 and s.r1 > s.r2 and r < s.r1 and s.r1 >= s.frac * s.rmax:
            phi = np.arctan2(abs(hy[k - 1]), abs(hx[k - 1]))
            tht = np.pi / 4 + s.pull * (phi - np.pi / 4)
            out.append(('slow', {'tht': tht}, (3, k, k * s.dt, np.rad2deg(phi), np.rad2deg(tht), 0, 0)))
            s.n_peak += 1
        s.rmax = max(s.rmax, r); s.r2, s.r1 = s.r1, r
        return out


VARIANTS = {
    'R': lambda dt: Tracked(dt),
    'peak': lambda dt: Peak(dt),                         # 주 재구현
    'peak_maxabs': lambda dt: Peak(dt, mag='maxabs'),    # r 정의 변형
    'peak_pull1': lambda dt: Peak(dt, pull=1.0),         # 순간 방향 그대로 (v19 11쪽 비교군). pull=0이면 45° 고정이 됨
}

_plants = {}


def job(args):
    name, j = args
    ax, ay, dt = load_records()[j]
    if dt not in _plants: _plants[dt] = Plant(dt)
    pol = VARIANTS[name](dt)
    y, dec, _ = simulate(_plants[dt], ax, ay, pol)
    return name, j, metrics(y).tolist(), float(np.rad2deg(pol.rot)), getattr(pol, 'n_peak', 0)


def summarize(res, unc):
    out = {}
    for name in VARIANTS:
        m = np.array([res[(name, j)][0] for j in range(15)])
        red = (1 - m / unc) * 100                     # 기록 × 6지표 저감률 (%)
        r6 = red.mean(1)
        evt = np.mean([r6[[i for i, e in enumerate(EVENT) if e == ev]].mean() for ev in ('IV', 'NR', 'KB', 'CC')])
        out[name] = dict(rec_mean=r6.mean(), evt_mean=evt, per_rec=r6.tolist(), per_metric=red.mean(0).tolist(),
                         rot_deg=float(np.mean([res[(name, j)][1] for j in range(15)])),
                         n_peak=int(sum(res[(name, j)][2] for j in range(15))),
                         th_max_red=red[:, 4].tolist())
    R = out['R']
    for name, o in out.items():
        o['rec_gain'] = o['rec_mean'] - R['rec_mean']; o['evt_gain'] = o['evt_mean'] - R['evt_mean']
        o['n_better'] = int(sum(a > b for a, b in zip(o['per_rec'], R['per_rec'])))
        o['n_thmax_worse'] = int(sum(a < b for a, b in zip(o['th_max_red'], R['th_max_red'])))
        o['rot_change'] = (o['rot_deg'] / R['rot_deg'] - 1) * 100
    return out


if __name__ == '__main__':
    t0 = time.time()
    unc = np.load(os.path.join(W8, 'reproduction_v2b', 'out_unc_zoh_up1.npy'))
    jobs = [(n, j) for n in VARIANTS for j in range(15)]
    res = {}
    with ProcessPoolExecutor(max_workers=min(15, os.cpu_count())) as ex:
        for name, j, m, rot, npk in ex.map(job, jobs):
            res[(name, j)] = (m, rot, npk); print(f'{name} rec{j + 1} done {time.time() - t0:.0f}s', flush=True)
    out = summarize(res, unc)
    # 회귀 확인: R은 8주차 regress_R 결과(15기록 평균 15.811 %)와 같아야 한다
    assert abs(out['R']['rec_mean'] - 15.811) < 0.01, out['R']['rec_mean']
    json.dump(out, open(os.path.join(HERE, 'peak_rule_result.json'), 'w'), indent=1)
    print(f"\n{'variant':12s} {'rec%':>6s} {'evt%':>6s} {'d_rec':>6s} {'d_evt':>6s} better thmax_worse rot%")
    for name, o in out.items():
        print(f"{name:12s} {o['rec_mean']:6.2f} {o['evt_mean']:6.2f} {o['rec_gain']:+6.2f} {o['evt_gain']:+6.2f}"
              f" {o['n_better']:5d}/15 {o['n_thmax_worse']:5d}/15 {o['rot_change']:+5.0f}")
    print('v19 target  ', V19)
