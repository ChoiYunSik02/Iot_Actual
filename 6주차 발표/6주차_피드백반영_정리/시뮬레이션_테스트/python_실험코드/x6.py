"""6주차 계획서 실험(X1~X5): 경보 없는 즉시 충격(반정현 펄스) + 판단 시간 예산 + 규칙/AI/Oracle"""
import sys, numpy as np, pickle
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim, pack, cost
from sim import DT, NSTEP, G, YMAX
T = np.arange(NSTEP)*DT
U_GRID = [0.5,0.7,1.0,1.4,2.0,2.8,4.0]
PGV_MAX = 3.0
def gen_pulse(rng, Tp=None, A=None, bld=None):
    while True:
        tp = Tp if Tp is not None else float(np.exp(rng.uniform(np.log(0.2), np.log(2.0))))
        a = A if A is not None else float(rng.uniform(0.2, 2.0))
        if a*G*tp/np.pi <= PGV_MAX or (Tp is not None and A is not None): break
    ag = np.zeros(NSTEP); n = int(tp/2/DT)
    ag[:n] = a*G*np.sin(2*np.pi*np.arange(n)*DT/tp)*rng.choice([-1,1]) if Tp is None else a*G*np.sin(2*np.pi*np.arange(n)*DT/tp)
    if bld is None: bld = rng.random() < 0.5   # True = B(강성 저하)
    fs = rng.uniform(0.95,1.02); fs2 = fs*0.85 if bld else fs
    return dict(ag=ag, F=np.zeros(NSTEP), jf=5, fscale=fs, fscale2=fs2, t_sw=1.5, zeta=rng.uniform(0.01,0.03),
                info=dict(Tp=tp, A=a, B=bld))
def mkpack(sc, rng): return pack.make_pack(sc, rng)
def run(p, mode, param=1.0, th3=None, record=False):
    th = np.zeros(sim.NTHETA)
    if th3 is not None: th[0],th[1],th[2] = th3
    return pack.run_pack(p, mode, param, th, record=record)
def trig_idx(ag):
    return int(np.argmax(np.abs(ag) > 0.3))
def metrics(p, m, hist=None):
    q = cost.ratios(m, p["m0"])
    out = dict(J=cost.J(m,p["m0"]), rms=q["rms"], pk=q["pk"], late=q["late"], ystroke=q["ystroke"])
    if hist is not None:
        n1 = int(0.6/DT); out["y_first"] = float(np.max(np.abs(hist[:n1,1]))/YMAX)
    return out
