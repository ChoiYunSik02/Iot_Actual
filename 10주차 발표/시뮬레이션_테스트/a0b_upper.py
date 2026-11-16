"""10주차 A0b: 지진 파형 1 s 뒤를 완벽히 알 때의 제어 상한 (계획 13절에 실행 전 고정). 개발 62쌍, test·test2 안 씀.

미래 정보(FUT)는 실제 지진 기록에서 바로 꺼낸다(완벽한 예측). 같은 규칙에 과거 정보(PAST)를 넣은 것도 같이 돌려,
이득이 '미래를 알아서'인지 '규칙을 바꿔서'인지 나눈다. 모든 방식에 같은 지령 지연(0, 0.5, 1.0 s)을 준다.

  LP_V        9주차 최종본 (기준)
  DIR_FUT     A-1: 피크 규칙이 회전판을 돌릴 때 방향을 '1 s 뒤 저역통과 지반 가속도 방향'으로 (45° 쪽 0.5 당김은 같음)
  DIR_PAST    같은 규칙, 지금 시점의 저역통과 지반 가속도 방향
  VUP_FUT     A-2: 1 s 뒤 세기 변화율 r > +0.2면 감쇠 최대(κ=0.1), r < −0.2면 감쇠 최소(κ=0.8), 그 사이는 원문 규칙
  VUP_PAST    같은 규칙, 지난 1 s의 세기 변화율
  VDN_FUT     A-2 반대 방향: r > +0.2면 κ=0.8, r < −0.2면 κ=0.1 (방향을 미리 모르므로 둘 다 본다)
  BOTH_FUT    DIR_FUT + VUP_FUT
python a0b_upper.py [--smoke]
"""
import os, sys, json, time, argparse
import numpy as np
from scipy.signal import butter, lfilter
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '9주차 발표', '시뮬레이션_테스트', 'peak_rule'))
import run_set as rs  # noqa: E402
from run_set import Plant, simulate, metrics, load, uncontrolled, RPolicy  # noqa: E402
from peak_v2 import PeakV2  # noqa: E402
from ground_ai import low_priority, log  # noqa: E402

POLS = ('LP_V', 'DIR_FUT', 'DIR_PAST', 'VUP_FUT', 'VUP_PAST', 'VDN_FUT', 'BOTH_FUT')
DELAYS = (0.0, 0.5, 1.0)
TAU = 0.2
OUT = os.path.join(HERE, 'results_a0b')


def ground_info(ax, ay, dt):
    """원 간격(dt)에서 저역통과 가속도(X·Y)와 2 s RMS 세기(합성). 필터는 인과."""
    b, c = butter(2, 1.0, fs=1 / dt); lx, ly = lfilter(b, c, ax), lfilter(b, c, ay)
    n2 = int(round(2 / dt)); e = np.sqrt(np.convolve(ax ** 2 + ay ** 2, np.ones(n2) / n2)[:len(ax)])
    return lx, ly, e


class Ctrl(PeakV2):
    """LP_V(PeakV2, gap 0, 밸브 매 스텝)에 지반 정보를 넣는 변형."""
    def __init__(s, dt, info, direction=None, valve=None):
        super().__init__(dt, gap=0.0); s.nc = 1
        s.lx, s.ly, s.e = info; s.H = int(round(1.0 / dt)); s.T = len(s.e)
        s.direction, s.valve = direction, valve  # None | 'FUT' | 'PAST' ; None | ('FUT'|'PAST', 'UP'|'DN')

    def decide(s, ob, hx, hy, th_act):
        out = super().decide(ob, hx, hy, th_act)
        if s.direction is None: return out
        k = ob.k; j = min(k + s.H, s.T - 1) if s.direction == 'FUT' else k
        phi = np.arctan2(abs(s.ly[j]), abs(s.lx[j])); tht = np.pi / 4 + s.pull * (phi - np.pi / 4)
        return [(kind, ({'tht': tht} if 'tht' in cmd else cmd), rec) for kind, cmd, rec in out]

    def decide_fast(s, ob, th_act):
        out = RPolicy.decide_fast(s, ob, th_act)
        if s.valve is None or not out: return out
        k = ob.k; src, sign = s.valve
        if src == 'FUT': a, b = s.e[k], s.e[min(k + s.H, s.T - 1)]
        else: a, b = s.e[max(k - s.H, 0)], s.e[k]
        r = (b - a) / (a + 1e-12)
        hi, lo = (0.1, 0.8) if sign == 'UP' else (0.8, 0.1)
        kap = hi if r > TAU else (lo if r < -TAU else out[0][1]['kap'])
        return [(out[0][0], {'kap': kap}, out[0][2])]


def make(pol, dt, info):
    return {'LP_V': lambda: Ctrl(dt, info), 'DIR_FUT': lambda: Ctrl(dt, info, 'FUT'), 'DIR_PAST': lambda: Ctrl(dt, info, 'PAST'),
            'VUP_FUT': lambda: Ctrl(dt, info, valve=('FUT', 'UP')), 'VUP_PAST': lambda: Ctrl(dt, info, valve=('PAST', 'UP')),
            'VDN_FUT': lambda: Ctrl(dt, info, valve=('FUT', 'DN')), 'BOTH_FUT': lambda: Ctrl(dt, info, 'FUT', ('FUT', 'UP'))}[pol]()


_plants = {}


def job(a):
    low_priority(); j, rec, pol, d = a
    ax, ay, dt = load(rec)
    if pol == 'U': return a, uncontrolled(ax, ay, dt).tolist()
    if dt not in _plants: _plants[dt] = Plant(dt)
    if len(_plants[dt].cache) > 200: _plants[dt].cache.clear()
    n = int(round(d / dt))
    y, _, _ = simulate(_plants[dt], ax, ay, make(pol, dt, ground_info(ax, ay, dt)), delay_slow=n, delay_fast=n)
    return a, metrics(y).tolist()


def ev(rec): return rec[1].replace(',', '').split()[0]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--smoke', action='store_true'); A = ap.parse_args()
    low_priority(); out = OUT + ('_smoke' if A.smoke else ''); os.makedirs(out, exist_ok=True); logp = os.path.join(out, 'run.log')
    recs = sum((rs.record_list(s) for s in ('paper15', 'dev', 'test', 'week8')), [])
    assert not ({r[0] for r in recs} & {r[0] for r in rs.record_list('test2')})
    if A.smoke: recs = sorted(recs, key=lambda r: os.path.getsize(r[3]))[:3]
    jobs = [(j, recs[j], 'U', 0.0) for j in range(len(recs))] + \
           [(j, recs[j], p, d) for d in DELAYS for p in POLS for j in range(len(recs))]
    t0 = time.time(); log(f'시작: {len(jobs)}회', logp)
    with ProcessPoolExecutor(max_workers=int(os.environ.get('WORKERS', 12))) as ex:
        res = {(a[0], a[2], a[3]): np.array(m) for a, m in ex.map(job, jobs, chunksize=2)}
    log(f'시뮬레이션 끝 {time.time() - t0:.0f}s', logp)
    # 회귀: LP_V 지연 0은 9주차 dev_final과 같은 정의여야 한다 (62쌍 R 대비 +3.02는 R이 없어 여기서 직접 대조하지 않음)
    U = {j: res[(j, 'U', 0.0)] for j in range(len(recs))}
    red = lambda j, p, d: float((1 - res[(j, p, d)] / U[j]).mean() * 100)
    evs = sorted({ev(r) for r in recs}); summ = {}
    for d in DELAYS:
        base = {j: red(j, 'LP_V', d) for j in range(len(recs))}
        summ[str(d)] = {'LP_V_score': float(np.mean(list(base.values())))}
        for p in POLS[1:]:
            dr = {j: red(j, p, d) - base[j] for j in range(len(recs))}
            de = np.array([np.mean([dr[j] for j in range(len(recs)) if ev(recs[j]) == e]) for e in evs])
            thw = sum(res[(j, p, d)][4] > res[(j, 'LP_V', d)][4] * (1 + 1e-9) for j in range(len(recs)))
            summ[str(d)][p] = dict(dS_evt=float(de.mean()), ci95=rs.boot_ci(de) if len(de) > 1 else [0, 0],
                                   ev_better=int((de > 0).sum()), ev_worse=int((de < 0).sum()), thmax_worse_rec=int(thw),
                                   per_event=dict(zip(evs, map(float, de))))
    json.dump(dict(n_pairs=len(recs), n_events=len(evs), tau=TAU, delays=DELAYS, summary=summ, minutes=(time.time() - t0) / 60),
              open(os.path.join(out, 'result_a0b.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    L = [f'# A0b 제어 상한 (자동 생성 {time.strftime("%Y-%m-%d %H:%M")}, {len(recs)}쌍 {len(evs)}사건)', '',
         '| 지연 | 방식 | LP_V 대비 사건 평균 %p | 95% 구간 | 나아진/나빠진 사건 | 비틀림 최대 악화 기록 |', '|---|---|---|---|---|---|']
    for d in DELAYS:
        L.append(f'| {d} s | LP_V (점수 {summ[str(d)]["LP_V_score"]:.2f}) | 0 | — | — | — |')
        for p in POLS[1:]:
            o = summ[str(d)][p]
            L.append(f'| {d} s | {p} | {o["dS_evt"]:+.2f} | [{o["ci95"][0]:+.2f}, {o["ci95"][1]:+.2f}] | {o["ev_better"]}/{o["ev_worse"]} | {o["thmax_worse_rec"]} |')
    open(os.path.join(out, '결과_자동요약.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    log('완료', logp); print('\n'.join(L))


if __name__ == '__main__':
    main()
