import numpy as np, sim, scen, cost
XI_OPT = 6.0
_WD = (np.zeros((1, sim.NWIN+1)), np.zeros(1), np.zeros(1, dtype=np.int64))
def make_pack(sc, rng):
    nz = scen.noise_arrays(rng)
    sysT = sim.make_system(sc["fscale"], sc["zeta"], True)
    sys0 = sim.make_system(sc["fscale"], sc["zeta"], False)
    sysT2 = sim.make_system(sc["fscale2"], sc["zeta"], True)
    sys02 = sim.make_system(sc["fscale2"], sc["zeta"], False)
    s_sw = int(sc["t_sw"] / sim.DT)
    dummy = np.zeros((1,6))
    m0 = sim.rollout(sc["ag"], sc["F"], sc["jf"], *sys0[:3], sys0[3], sys0[4], sys0[5], sys0[6], XI_OPT,
                     0, 1.0, np.zeros(sim.NTHETA), nz[0], nz[1], False, dummy, np.zeros((1,sim.NF)), np.zeros((1,2)), np.zeros(1,dtype=np.int64), 0.0,
                     sys02[0], sys02[1], s_sw, np.zeros(sim.NEST), 0, sc["fscale2"], sc["fscale"], *_WD)
    return dict(sc=sc, nz=nz, sysT=sysT, sysT2=sysT2, sys0=sys0, sys02=sys02, s_sw=s_sw, m0=m0)
_WD = (np.zeros((1, sim.NWIN+1)), np.zeros(1), np.zeros(1, dtype=np.int64))
_FD = np.zeros((1, sim.NF)); _AD = np.zeros((1, 2)); _CN = np.zeros(1, dtype=np.int64)
def run_pack(p, mode, param=1.0, theta=None, record=False, data=None, pneu=0.0, gmode=0, est=None, wd=None):
    s = p["sys0"] if mode == 0 else p["sysT"]
    s2 = p["sys02"] if mode == 0 else p["sysT2"]
    th = theta if theta is not None else np.zeros(sim.NTHETA)
    hist = np.zeros((sim.NSTEP,6)) if record else np.zeros((1,6))
    sc = p["sc"]
    m = sim.rollout(sc["ag"], sc["F"], sc["jf"], s[0], s[1], s[2], s[3], s[4], s[5], s[6], XI_OPT,
                    mode, param, th, p["nz"][0], p["nz"][1], record, hist,
                    *(data if data is not None else (_FD, _AD, _CN)), pneu,
                    s2[0], s2[1], p["s_sw"], est if est is not None else np.zeros(sim.NEST), gmode,
                    sc["fscale2"], sc["fscale"], *(wd if wd is not None else _WD))
    return (m, hist) if record else m
def make_set(seed, n, level=None):
    rng = np.random.default_rng(seed)
    return [make_pack(scen.gen_scenario(rng, level=level), rng) for _ in range(n)]
def evaluate(packs, mode, param=1.0, theta=None, gmode=0, est=None):
    out = []
    for p in packs:
        m = run_pack(p, mode, param, theta, gmode=gmode, est=est)
        out.append((cost.J(m, p["m0"]), cost.ratios(m, p["m0"])))
    return out
def summarize(res):
    keys = res[0][1].keys()
    d = {k: float(np.mean([r[1][k] for r in res])) for k in keys}
    d["J"] = float(np.mean([r[0] for r in res]))
    d["over100%"] = float(np.mean([r[1]["ystroke"] > 1.0 for r in res]))
    return d
