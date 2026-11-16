"""AI 밸브 제어기 NN_V (사전 등록: 9주차_계획.md 9절). 개발 62쌍, 19사건 사건 빼기. test2는 쓰지 않는다.
학습은 LP_V 회전판·펌프 궤적을 고정한 미분 가능 시뮬레이션, 평가는 되먹임이 있는 실제 simulate로 한다.
python valve_nn.py cache  /  python valve_nn.py run [기록수]   (EPOCHS 환경변수는 파일럿 전용)
"""
import os, sys, json, time
import numpy as np
import torch
import torch.nn as nn
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled
from peak_v2 import PeakV2
from run_test2 import POL
from rs_ref import cdamp, kappa
from tlcd3 import IDX, N
from valve_oracle import met

CACHE = os.environ['NN_CACHE']
EPOCHS = int(os.environ.get('EPOCHS', 40)); T_TRAIN = 40.0; WORKERS = int(os.environ.get('WORKERS', 14))
n_ = 3 * N + 2; I = IDX
IV = [n_ + I['xd'], n_ + I['yd']]; IT = [n_ + I['xt'], n_ + I['yt']]; OUT = [I['xt'], I['yt'], I['tt']]
KG = np.linspace(0.1, 0.8, 20001); CG = np.array([cdamp(q) for q in KG])
LCMIN, LCMAX = float(np.log(CG.min())), float(np.log(CG.max()))
NF = 13; V0, A0 = 0.5, 2.0
torch.set_default_dtype(torch.float64)


def EV(r):
    """사건 이름. 'Kobe Japan'과 'Kobe, Japan'처럼 표기만 다른 것은 같은 사건이다 (peak_v2.gains와 같은 규칙)."""
    return r[1].replace(',', '').split()[0]


def net():
    m = nn.Sequential(nn.Linear(NF, 32), nn.Tanh(), nn.Linear(32, 32), nn.Tanh(), nn.Linear(32, 1))
    nn.init.zeros_(m[-1].weight); nn.init.zeros_(m[-1].bias)
    return m


def recs62():
    r = sum((rs.record_list(s) for s in ('paper15', 'dev', 'test', 'week8')), [])
    assert not ({a[0] for a in r} & {a[0] for a in rs.record_list('test2')})
    return r


class Mem:
    """인과 이동평균 (시상수 3 s). 학습과 실제 평가에서 같은 코드를 쓴다."""
    def __init__(s, dt):
        s.a = 1 - np.exp(-dt / 3.0); s.v = torch.zeros(2); s.g = torch.zeros(2)

    def feat(s, vr, aa, th):
        s.v = s.v + s.a * (vr.detach().abs() - s.v); s.g = s.g + s.a * (aa.detach().abs() - s.g)
        c, sn = torch.cos(th), torch.sin(th); ax_ = c * vr[0] + sn * vr[1]
        sx, sy = ax_ * c * aa[0], ax_ * sn * aa[1]
        return torch.stack([ax_ / V0, vr[0] / V0, vr[1] / V0, aa[0] / A0, aa[1] / A0, sx / (V0 * A0), sy / (V0 * A0), c, sn,
                            s.v[0] / V0, s.v[1] / V0, s.g[0] / A0, s.g[1] / A0])


def lc_rule(vr, aa, th):
    c, sn = np.cos(th), np.sin(th); ax_ = c * float(vr[0]) + sn * float(vr[1])
    return float(np.log(cdamp(kappa(ax_ * c * float(aa[0]), ax_ * sn * float(aa[1])))))


def lc_out(m, f, lr):
    return torch.clamp(lr + 2.5 * torch.tanh(m(f)[0]), LCMIN, LCMAX)


class NNV(PeakV2):
    def __init__(s, dt, m):
        super().__init__(dt, gap=0.0); s.nc = 1; s.m = m; s.mem = Mem(dt)

    def decide_fast(s, ob, th_act):
        vr, aa = torch.tensor(ob.vd - ob.vt), torch.tensor(ob.aa); th = torch.tensor(float(th_act))
        with torch.no_grad():
            lc = float(lc_out(s.m, s.mem.feat(vr, aa, th), lc_rule(vr, aa, float(th))))
        if ob.k == 0: return []  # 원문 규칙과 같이 k=0에는 밸브 지령 없음
        return [('fast', {'kap': float(np.interp(np.exp(lc), CG[::-1], KG[::-1]))}, (2, ob.k, ob.k * s.dt, 0, 0, 0, 0))]


def build(a):
    j, rec = a; ax, ay, dt = load(rec); p = Plant(dt)
    y0, _, st = simulate(p, ax, ay, POL['LP_V'](dt)); T = min(len(ax), int(round(T_TRAIN / dt)))
    keys, idx, D = {}, [], []
    for s in st[:T]:
        key = (s[4], round(float(np.deg2rad(s[3])), 4))
        if key not in keys: keys[key] = len(D); D.append(p.disc(*key))
        idx.append(keys[key])
    np.savez(os.path.join(CACHE, f'{j}.npz'), Ad=np.array([d[0] for d in D]), Bd=np.array([d[1] for d in D]), idx=np.array(idx),
             th=np.deg2rad([s[2] for s in st[:T]]), ax=ax[:T], ay=ay[:T], dt=dt, U=uncontrolled(ax, ay, dt), m0=metrics(y0))
    return j


def grad(a):
    """기록 하나의 손실과 기울기. 궤적은 LP_V로 고정."""
    torch.set_num_threads(1); j, sd = a; m = net(); m.load_state_dict(sd)
    d = np.load(os.path.join(CACHE, f'{j}.npz')); Ad = torch.tensor(d['Ad']); Bd = torch.tensor(d['Bd']); idx = d['idx']
    ax = torch.tensor(d['ax']); ay = torch.tensor(d['ay']); th = torch.tensor(d['th']); dt = float(d['dt']); U = torch.tensor(d['U'])
    x = torch.zeros(2 * n_); vp = torch.zeros(2); mem = Mem(dt); ys = []
    for k in range(len(ax)):
        ys.append(x[OUT]); vt = x[IT]; vr = x[IV] - vt
        aa = ((vt - vp) / dt if k else torch.zeros(2)) + torch.stack([ax[k], ay[k]]); vp = vt.detach()
        lc = lc_out(m, mem.feat(vr, aa.detach(), th[k]), lc_rule(vr.detach(), aa.detach(), float(th[k])))
        F = torch.exp(lc) * vr.abs() * vr
        x = Ad[idx[k]] @ x + Bd[idx[k]] @ torch.cat([ax[k:k + 1], ay[k:k + 1], F])
    L = (met(torch.stack(ys)) / U).mean(); L.backward()
    return float(L), [p.grad.numpy() for p in m.parameters()]


def evaluate(a):
    torch.set_num_threads(1); j, rec, sd = a; ax, ay, dt = load(rec); m = net(); m.load_state_dict(sd)
    y, _, _ = simulate(Plant(dt), ax, ay, NNV(dt, m))
    return j, metrics(y).tolist()


def train(ex, tr, ev_w):
    m = net(); opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    for e in range(EPOCHS):
        sd = {k: v.clone() for k, v in m.state_dict().items()}
        R = list(ex.map(grad, [(j, sd) for j in tr], chunksize=1)); w = np.array([ev_w[j] for j in tr]); w = w / w.sum()
        for i, p in enumerate(m.parameters()): p.grad = torch.tensor(sum(wi * r[1][i] for wi, r in zip(w, R)))
        nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step()
        if e % 5 == 0 or e == EPOCHS - 1: print(f'  epoch {e} loss {sum(wi * r[0] for wi, r in zip(w, R)):.5f}', flush=True)
    return {k: v.clone() for k, v in m.state_dict().items()}


if __name__ == '__main__':
    recs = recs62(); os.makedirs(CACHE, exist_ok=True); lim = int(sys.argv[2]) if len(sys.argv) > 2 else len(recs)
    order = sorted(range(len(recs)), key=lambda j: os.path.getsize(recs[j][3]))[:lim]
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(build, [(j, recs[j]) for j in order if not os.path.exists(os.path.join(CACHE, f'{j}.npz'))]))
        if sys.argv[1] == 'cache': sys.exit()
        C = {j: np.load(os.path.join(CACHE, f'{j}.npz')) for j in order}; U = {j: C[j]['U'] for j in order}; m0 = {j: C[j]['m0'] for j in order}
        # 회귀: 출력 0 신경망은 LP_V와 같아야 한다
        zero = {k: v.clone() for k, v in net().state_dict().items()}
        for j, m in ex.map(evaluate, [(j, recs[j], zero) for j in order[:2]]):
            assert np.abs(np.array(m) / m0[j] - 1).max() < 2e-3, (recs[j][0], m, m0[j])
        print('zero-net = LP_V ok', flush=True)
        evs = sorted({EV(recs[j]) for j in order}); cnt = {e: sum(EV(recs[j]) == e for j in order) for e in evs}
        w = {j: 1 / cnt[EV(recs[j])] for j in order}; res = {}; t0 = time.time()
        assert lim != len(recs) or len(evs) == 19, evs
        CK = f'valve_nn_ckpt_e{EPOCHS}_n{lim}.jsonl'; done = set()  # 사건별 중간 저장
        if os.path.exists(CK):
            for line in open(CK, encoding='utf-8'):
                e, r = json.loads(line); done.add(e); res.update({int(j): np.array(m) for j, m in r.items()})
            print('checkpoint folds', len(done), flush=True)
        for f, e in enumerate(evs):
            if e in done: continue
            test = [j for j in order if EV(recs[j]) == e]; tr = [j for j in order if EV(recs[j]) != e]
            print(f'fold {f + 1}/{len(evs)} {e} n_test {len(test)} {time.time() - t0:.0f}s', flush=True)
            sd = train(ex, tr, w)
            for j, m in ex.map(evaluate, [(j, recs[j], sd) for j in test]): res[j] = np.array(m)
            with open(CK, 'a', encoding='utf-8') as fh: fh.write(json.dumps([e, {str(j): res[j].tolist() for j in test}]) + '\n')
            print('  fold gain', round(float(np.mean([((m0[j] - res[j]) / U[j]).mean() * 100 for j in test])), 3), flush=True)
    d = {j: float(((m0[j] - res[j]) / U[j]).mean() * 100) for j in order}
    de = np.array([np.mean([d[j] for j in order if EV(recs[j]) == e]) for e in evs])
    out = dict(n_pairs=len(order), n_events=len(evs), epochs=EPOCHS, NN_V_minus_LP_V_evt=float(de.mean()), ci95=rs.boot_ci(de),
               events_better=int((de > 0).sum()), events_worse=int((de < 0).sum()), rec_better=int(sum(v > 0 for v in d.values())),
               per_event=dict(zip(evs, map(float, de))), per_rec={recs[j][0]: d[j] for j in order},
               NN_metrics={recs[j][0]: res[j].tolist() for j in order})
    print(json.dumps({k: v for k, v in out.items() if k not in ('per_rec', 'NN_metrics')}, ensure_ascii=False, indent=1))
    if lim == len(recs) and EPOCHS == 40:
        json.dump(out, open('result_valve_nn.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
