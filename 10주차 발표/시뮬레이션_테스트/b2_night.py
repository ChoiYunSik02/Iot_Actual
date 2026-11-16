"""10주차 B2·B3 밤 학습 (설정은 10주차_계획.md 14절에 실행 전 고정). 개발 62쌍 19사건 사건 빼기, test·test2 안 씀.

  python b2_night.py imit [--smoke]   B2 모방: 상한 해 log c*를 입력 13개(LIN13, NN13) 또는 15개(+지진 세기 변화 예측 A2x·A2y,
                                      LIN15, NN15)로 따라 한다. 평가는 되먹임 simulate.
  python b2_night.py b3 [--smoke]     B3 역전파 학습 수정판: 로짓 잔차 출력(잘림 없음), 10 s 구간, 미니배치 6, 300회 갱신,
                                      입력 13개(B3_13)와 15개(B3_15). 출력 0 초기값 = 원문 규칙.
  python b2_night.py b3l [--smoke]    B3과 같고 갱신 1000회, 학습률 1e-2 (2차, 학습량 부족 가설 확인).
  python b2_night.py b3s [--smoke]    b3l과 같은 설정, 입력 13, 시드 1·2 반복 + 고정 검증 구간 손실 기록 (계획 15.2).
  python b2_night.py b3lin [--smoke] b3l과 같은 학습법, 정책만 선형(13→1), 시드 0 + 고정 검증 손실 (계획 16, 신경망 기여 대조).
  python b2_night.py full [--smoke]  B3_13(b3l 설정)을 62쌍 전체로 시드 0·1·2 학습, 가중치만 저장 (계획 17).
  python b2_night.py all              imit, b3, b3l 순서. 각 부분은 끝나면 요약을 커밋·push·알림한다.
다시 실행하면 끝난 겹(results_b2/<부분>/fold_XX.json)과 끝난 부분(DONE)은 건너뛴다.
"""
import os, sys, json, time, argparse
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
OUTROOT = os.path.join(HERE, 'results_b2')
import b0_diag  # noqa: E402  (NN_CACHE 기본값과 9주차 경로를 잡는다)
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import run_set as rs  # noqa: E402
from run_set import simulate, metrics, load, Plant  # noqa: E402
import valve_nn as vn  # noqa: E402
from valve_oracle import met  # noqa: E402
import ground_ai as ga  # noqa: E402
from ground_ai import log, notify, git_commit, low_priority, REPO  # noqa: E402

ORACLE = b0_diag.ORACLE
LCMIN, LCMAX = vn.LCMIN, vn.LCMAX
A0 = vn.A0
SEG, MB, UPD, LR_B3 = 10.0, 6, 300, 3e-3
NVAL = 12  # 계획 15.2 고정 검증 구간 수
SMOKE = False


# ---------- 지진 세기 변화 예측 (A0a LIN_SELF와 같은 식, 겹마다 다시 적합) ----------
def ridge_w(X, y, lam=1e-2):
    A = np.c_[X, np.ones(len(X))]
    return np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ y)


def a2_weights(D, recs, ev_test):
    X, Y, _, _, R = D
    tr = np.array([vn.EV(recs[r]) != ev_test for r in R])
    return [ridge_w(ga.self_hist(X[tr], j), Y[tr, j]) for j in (2, 3)]


def a2_series(rec, W2):
    """매 시뮬레이션 스텝의 A2x·A2y 예측(절대값/A0). 0.05 s 앞 격자점까지만 써서 인과."""
    ax, ay, dt = load(rec)
    (a8x, _, evx), (a8y, _, evy) = ga.series(ax, dt), ga.series(ay, dt)
    n = min(len(a8x), len(a8y)); Wn = ga.W
    sv = lambda v: np.lib.stride_tricks.sliding_window_view(v[:n], Wn)
    s = np.maximum(np.abs(sv(a8x)).max(1), np.abs(sv(a8y)).max(1)) + 1e-12
    g = np.zeros((n, 2))
    for c, (ev, w) in enumerate(zip((evx, evy), W2)):
        g[Wn - 1:, c] = (np.c_[sv(ev) / s[:, None], np.ones(len(s))] @ w) * s
    gi = np.floor(np.arange(len(ax)) * dt * ga.FS).astype(int) - 1
    out = np.where((gi >= Wn - 1)[:, None], g[np.clip(gi, 0, n - 1)], 0.0)
    return out / A0


# ---------- 제어기 ----------
class LinF:
    def __init__(s, w): s.w = w
    def __call__(s, f, lr): return float(np.clip(np.r_[f, 1.0] @ s.w, LCMIN, LCMAX))


def mlp(nf):
    m = nn.Sequential(nn.Linear(nf, 32), nn.Tanh(), nn.Linear(32, 32), nn.Tanh(), nn.Linear(32, 1))
    nn.init.zeros_(m[-1].weight); nn.init.zeros_(m[-1].bias)
    return m


def policy(nf, arch='mlp'):
    """B3 정책. lin = 선형(nf→1, 0 초기값, 계획 16절 대조). 둘 다 출력 0 = 원문 규칙."""
    if arch == 'mlp': return mlp(nf)
    m = nn.Linear(nf, 1); nn.init.zeros_(m.weight); nn.init.zeros_(m.bias)
    return m


class NNF:
    """모방 신경망 (시드 평균). log c = LCMIN + (LCMAX − LCMIN)·sigmoid(출력)."""
    def __init__(s, sds, nf): s.ms = [mlp(nf) for _ in sds]; [m.load_state_dict(d) for m, d in zip(s.ms, sds)]
    def __call__(s, f, lr):
        x = torch.tensor(f)
        with torch.no_grad(): return float(np.mean([LCMIN + (LCMAX - LCMIN) * torch.sigmoid(m(x)[0]).item() for m in s.ms]))


def zr_of(lr):
    q = (lr - LCMIN) / (LCMAX - LCMIN)
    q = q.clamp(0.02, 0.98) if torch.is_tensor(q) else float(np.clip(q, 0.02, 0.98))
    return torch.log(q / (1 - q)) if torch.is_tensor(q) else float(np.log(q / (1 - q)))


class ResF:
    """B3: log c = LCMIN + (LCMAX − LCMIN)·sigmoid(logit(원문 규칙) + 신경망). 출력 0 = 원문 규칙(끝값만 0.02 안쪽)."""
    def __init__(s, sd, nf, arch='mlp'): s.m = policy(nf, arch); s.m.load_state_dict(sd)
    def __call__(s, f, lr):
        with torch.no_grad(): return LCMIN + (LCMAX - LCMIN) / (1 + np.exp(-(zr_of(lr) + s.m(torch.tensor(f))[0].item())))


class Ctl(vn.NNV):
    def __init__(s, dt, f, extra=None): super().__init__(dt, None); s.f = f; s.extra = extra

    def decide_fast(s, ob, th_act):
        vr, aa = torch.tensor(ob.vd - ob.vt), torch.tensor(ob.aa); th = float(th_act)
        with torch.no_grad(): f = s.mem.feat(vr, aa, torch.tensor(th)).numpy()
        if s.extra is not None: f = np.r_[f, s.extra[min(ob.k, len(s.extra) - 1)]]
        lc = s.f(f, vn.lc_rule(vr, aa, th))
        if ob.k == 0: return []
        return [('fast', {'kap': float(np.interp(np.exp(lc), vn.CG[::-1], vn.KG[::-1]))}, (2, ob.k, ob.k * s.dt, 0, 0, 0, 0))]


def evaluate(a):
    torch.set_num_threads(1); low_priority(); key, rec, f, extra = a; ax, ay, dt = load(rec)
    y, _, _ = simulate(Plant(dt), ax, ay, Ctl(dt, f, extra))
    return key, metrics(y)


# ---------- 공통 ----------
def recs62(): return b0_diag.recs62()


def summarize(name, recs, idx, res, models, outdir, logp, extra_info):
    evs = sorted({vn.EV(recs[j]) for j in idx}); out = dict(n_pairs=len(idx), n_events=len(evs), **extra_info)
    base = {}
    for j in idx:
        z = np.load(os.path.join(ORACLE, f'rec_{j:02d}.npz')); base[j] = (z['m0'], z['U'])
    L = [f'# {name} (자동 생성 {time.strftime("%Y-%m-%d %H:%M")}, {len(idx)}쌍 {len(evs)}사건)', '',
         '| 방식 | LP_V 대비 사건 평균 %p | 95% 구간 | 나아진/나빠진 사건 | 비틀림 최대 악화 기록 | 사전 채택 기준 |', '|---|---|---|---|---|---|']
    for mname in models:
        d = {j: float(((base[j][0] - res[(mname, j)]) / base[j][1]).mean() * 100) for j in idx}
        de = np.array([np.mean([d[j] for j in idx if vn.EV(recs[j]) == e]) for e in evs])
        ci = rs.boot_ci(de) if len(de) > 1 else [0.0, 0.0]
        thw = int(sum(res[(mname, j)][4] > base[j][0][4] * (1 + 1e-9) for j in idx))
        ok = bool(de.mean() > 0 and ci[0] > 0 and (de > 0).sum() > (de < 0).sum())
        out[mname] = dict(dS_evt=float(de.mean()), ci95=ci, ev_better=int((de > 0).sum()), ev_worse=int((de < 0).sum()),
                          thmax_worse_rec=thw, adopt=ok, per_event=dict(zip(evs, map(float, de))))
        L.append(f'| {mname} | {de.mean():+.2f} | [{ci[0]:+.2f}, {ci[1]:+.2f}] | {(de > 0).sum()}/{(de < 0).sum()} | {thw} | {"채택" if ok else "불채택"} |')
    json.dump(out, open(os.path.join(outdir, 'result.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(os.path.join(outdir, '결과_자동요약.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    log('\n'.join(L), logp)
    return out


def finish(part, outdir, logp, out, models, t0):
    open(os.path.join(outdir, 'DONE'), 'w').write(time.strftime('%Y-%m-%d %H:%M:%S'))
    best = max(models, key=lambda m: out[m]['dS_evt'])
    msg = f'10주차 {part} 결과(자동): 최고 {best} {out[best]["dS_evt"]:+.2f}%p, 채택 ' + (','.join(m for m in models if out[m]['adopt']) or '없음')
    if SMOKE: log('smoke: 커밋·알림 생략', logp); return
    rel = os.path.relpath(outdir, REPO)
    git_commit([os.path.join(rel, n) for n in ('result.json', '결과_자동요약.md', 'run.log', 'DONE')], msg, logp)
    notify(msg + f' ({(time.time() - t0) / 60:.0f}분)', logp)


# ---------- B2 모방 ----------
def imit_feats(a):
    """상한 해 궤적을 따라 Mem 특징 13개와 라벨 log c* (0.05 s 간격, b0_diag (c)와 같은 표본)."""
    torch.set_num_threads(1); low_priority(); j, rec = a
    z = np.load(os.path.join(ORACLE, f'rec_{j:02d}.npz')); F, y, dt = b0_diag.feats_along(z, rec)
    s = max(1, int(round(0.05 / dt))); k = np.arange(1, len(y), s)
    return j, F[k], y[k], k


def fit_nn(Xtr, ytr, Xva, yva, seed, max_epochs):
    torch.manual_seed(seed); rng = np.random.default_rng(seed); m = mlp(Xtr.shape[1]); opt = torch.optim.Adam(m.parameters(), 1e-3)
    out = lambda X: LCMIN + (LCMAX - LCMIN) * torch.sigmoid(m(X)[:, 0])
    xt, yt, xv, yv = map(torch.tensor, (Xtr, ytr, Xva, yva)); best, bs, bad = np.inf, None, 0
    for ep in range(max_epochs):
        for b in np.array_split(rng.permutation(len(xt)), max(1, len(xt) // 256)):
            opt.zero_grad(); loss = ((out(xt[b]) - yt[b]) ** 2).mean(); loss.backward(); opt.step()
        with torch.no_grad(): v = float(((out(xv) - yv) ** 2).mean())
        if v < best - 1e-7: best, bs, bad = v, {k: x.clone() for k, x in m.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= 10: break
    return bs, ep + 1


def part_imit(recs, ex, D, t0):
    outdir = os.path.join(OUTROOT, 'imit' + ('_smoke' if SMOKE else '')); os.makedirs(outdir, exist_ok=True); logp = os.path.join(outdir, 'run.log')
    if os.path.exists(os.path.join(outdir, 'DONE')): log('imit 이미 완료', logp); return
    idx = list(range(len(recs)))
    if SMOKE: idx = sorted(idx, key=lambda j: os.path.getsize(recs[j][3]))[:6]
    evs = sorted({vn.EV(recs[j]) for j in idx}); log(f'imit 시작: {len(idx)}쌍 {len(evs)}사건', logp)
    FE = {j: (F, y, k) for j, F, y, k in ex.map(imit_feats, [(j, recs[j]) for j in idx])}; log('특징 계산 끝', logp)
    models = ('LIN13', 'NN13', 'LIN15', 'NN15'); res = {}; info = {}
    for fi, e in enumerate(evs):
        fp = os.path.join(outdir, f'fold_{fi:02d}.json')
        if os.path.exists(fp):
            r = json.load(open(fp, encoding='utf-8')); res.update({(m, int(j)): np.array(v) for m, d in r['res'].items() for j, v in d.items()})
            info[e] = r['info']; continue
        tk = time.time(); W2 = a2_weights(D, recs, e)
        A2 = {j: a2_series(recs[j], W2) for j in idx}
        te = [j for j in idx if vn.EV(recs[j]) == e]; trall = [j for j in idx if vn.EV(recs[j]) != e]
        tr_ev = sorted({vn.EV(recs[j]) for j in trall})
        va_ev = set(np.random.default_rng(1000 + fi).choice(tr_ev, min(3, len(tr_ev) - 1), replace=False)) if len(tr_ev) > 1 else set()
        fs = {}; fi_info = {}
        for nf in (13, 15):
            Xf = lambda J: np.vstack([np.c_[FE[j][0], A2[j][FE[j][2]]] if nf == 15 else FE[j][0] for j in J])
            Yf = lambda J: np.concatenate([FE[j][1] for j in J])
            fs[f'LIN{nf}'] = LinF(ridge_w(Xf(trall), Yf(trall), 1e-3))
            tr = [j for j in trall if vn.EV(recs[j]) not in va_ev]; va = [j for j in trall if vn.EV(recs[j]) in va_ev] or tr
            sds = []
            for sd in (0, 1, 2):
                st, ep = fit_nn(Xf(tr), Yf(tr), Xf(va), Yf(va), sd, 5 if SMOKE else 300); sds.append(st); fi_info[f'NN{nf}_ep{sd}'] = ep
            fs[f'NN{nf}'] = NNF(sds, nf)
        jobs = [((m, j), recs[j], fs[m], A2[j] if m.endswith('15') else None) for m in models for j in te]
        rr = dict(ex.map(evaluate, jobs))
        res.update(rr); info[e] = fi_info
        json.dump(dict(res={m: {str(j): rr[(m, j)].tolist() for j in te} for m in models}, info=fi_info),
                  open(fp, 'w', encoding='utf-8'))
        log(f'겹 {fi + 1}/{len(evs)} {e}: {time.time() - tk:.0f}s {fi_info}', logp)
    out = summarize('B2 모방 학습 (상한 해 따라 하기)', recs, idx, res, models, outdir, logp, dict(fold_info=info, minutes=(time.time() - t0) / 60))
    finish('B2 모방', outdir, logp, out, models, t0)


# ---------- B3 역전파 ----------
def start_states(j):
    """원문 규칙(LP_V) 궤적의 1 s 간격 상태(x, vp, Mem). 구간 학습의 시작점."""
    torch.set_num_threads(1); low_priority()
    d = np.load(os.path.join(vn.CACHE, f'{j}.npz')); Ad = torch.tensor(d['Ad']); Bd = torch.tensor(d['Bd']); idx = d['idx']
    ax = torch.tensor(d['ax']); ay = torch.tensor(d['ay']); th = torch.tensor(d['th']); dt = float(d['dt'])
    x = torch.zeros(2 * vn.n_); vp = torch.zeros(2); mem = vn.Mem(dt); per = int(round(1 / dt)); S = []
    with torch.no_grad():
        for k in range(len(ax)):
            vt = x[vn.IT]; vr = x[vn.IV] - vt; aa = ((vt - vp) / dt if k else torch.zeros(2)) + torch.stack([ax[k], ay[k]])
            if k % per == 0: S.append(np.r_[x.numpy(), vp.numpy(), mem.v.numpy(), mem.g.numpy()])
            vp = vt.clone(); mem.feat(vr, aa, th[k]); lc = vn.lc_rule(vr, aa, float(th[k]))
            x = Ad[idx[k]] @ x + Bd[idx[k]] @ torch.cat([ax[k:k + 1], ay[k:k + 1], np.exp(lc) * vr.abs() * vr])
    return j, np.array(S)


def seg_loss(m, j, s0, S, a2):
    d = np.load(os.path.join(vn.CACHE, f'{j}.npz')); dt = float(d['dt']); per = int(round(1 / dt)); k0 = s0 * per
    k1 = min(len(d['ax']), k0 + int(round(SEG / dt)))
    Ad = torch.tensor(d['Ad']); Bd = torch.tensor(d['Bd']); idx = d['idx']; U = torch.tensor(d['U'])
    ax = torch.tensor(d['ax']); ay = torch.tensor(d['ay']); th = torch.tensor(d['th'])
    n2 = 2 * vn.n_; st = torch.tensor(S[s0]); x = st[:n2].clone(); vp = st[n2:n2 + 2].clone(); mem = vn.Mem(dt)
    mem.v = st[n2 + 2:n2 + 4].clone(); mem.g = st[n2 + 4:n2 + 6].clone(); ys = []
    for k in range(k0, k1):
        ys.append(x[vn.OUT]); vt = x[vn.IT]; vr = x[vn.IV] - vt
        aa = ((vt - vp) / dt if k else torch.zeros(2)) + torch.stack([ax[k], ay[k]]); vp = vt.detach()
        f = mem.feat(vr, aa.detach(), th[k])
        if a2 is not None: f = torch.cat([f, torch.tensor(a2[k])])
        lr = vn.lc_rule(vr.detach(), aa.detach(), float(th[k]))
        lc = LCMIN + (LCMAX - LCMIN) * torch.sigmoid(zr_of(lr) + m(f)[0])
        x = Ad[idx[k]] @ x + Bd[idx[k]] @ torch.cat([ax[k:k + 1], ay[k:k + 1], torch.exp(lc) * vr.abs() * vr])
    return (met(torch.stack(ys)) / U).mean()


def b3_fold(a):
    """겹 하나: 학습(300회 갱신) 후 시험 사건 되먹임 평가. 한 프로세스에서 직렬."""
    torch.set_num_threads(1); low_priority(); torch.set_default_dtype(torch.float64)
    nf, fi, e, recs, tr, te, w, SS, A2, upd, lr, seed, arch = a
    torch.manual_seed(fi + 1000 * seed); rng = np.random.default_rng(100 + fi + 1000 * seed); m = policy(nf, arch); opt = torch.optim.Adam(m.parameters(), lr)
    p = np.array([w[j] for j in tr]); p /= p.sum(); hist = []; t0 = time.time()
    # 계획 15.2: 고정 검증 구간(학습 사건에서, 시드와 무관하게 겹마다 같은 12개)의 손실을 50회마다 기록. seed 0 신경망(b3l)은 기록 안 함, 선형(16절)은 기록
    vr_ = np.random.default_rng(5000 + fi); VS = [(j, int(vr_.integers(0, max(0, len(SS[j]) - int(SEG)) + 1))) for j in vr_.choice(tr, NVAL, p=p)] if (seed or arch == 'lin') else []
    vloss = lambda: float(np.mean([float(seg_loss(m, j, s0, SS[j], A2[j] if nf == 15 else None)) for j, s0 in VS]))
    val = []
    for u in range(upd):
        if VS and u % 50 == 0:
            with torch.no_grad(): val.append(vloss())
        opt.zero_grad(); tot = 0.0
        for j in rng.choice(tr, MB, p=p):
            nmax = max(0, len(SS[j]) - int(SEG)); s0 = int(rng.integers(0, nmax + 1))
            L = seg_loss(m, j, s0, SS[j], A2[j] if nf == 15 else None) / MB; L.backward(); tot += float(L)
        opt.step(); hist.append(tot)
    if VS:
        with torch.no_grad(): val.append(vloss())
    sd = {k: v.clone() for k, v in m.state_dict().items()}; f = ResF(sd, nf, arch)
    res = {j: evaluate((j, recs[j], f, A2[j] if nf == 15 else None))[1].tolist() for j in te}
    inf = dict(loss_first20=float(np.mean(hist[:20])), loss_last20=float(np.mean(hist[-20:])), minutes=(time.time() - t0) / 60)
    if val: inf.update(val_first=val[0], val_last=val[-1], val_curve=val)
    if arch == 'lin': inf['w'] = sd['weight'][0].tolist() + sd['bias'].tolist()  # 16절: 선형 가중치 기록(해석용)
    if not te: inf['state'] = {k: v.tolist() for k, v in sd.items()}  # 계획 17: 62쌍 전체 학습은 가중치만 저장
    return nf, fi, e, seed, res, inf


def part_b3(recs, ex, D, t0, name='b3', upd=UPD, lr=LR_B3, nfs=(13, 15), seeds=(0,), arch='mlp'):
    outdir = os.path.join(OUTROOT, name + ('_smoke' if SMOKE else '')); os.makedirs(outdir, exist_ok=True); logp = os.path.join(outdir, 'run.log')
    if os.path.exists(os.path.join(outdir, 'DONE')): log(f'{name} 이미 완료', logp); return
    idx = list(range(len(recs)))
    if SMOKE: idx = sorted(idx, key=lambda j: os.path.getsize(recs[j][3]))[:4]
    os.makedirs(vn.CACHE, exist_ok=True)
    list(ex.map(vn.build, [(j, recs[j]) for j in idx if not os.path.exists(os.path.join(vn.CACHE, f'{j}.npz'))]))
    SS = dict(ex.map(start_states, idx)); evs = sorted({vn.EV(recs[j]) for j in idx})
    cnt = {e: sum(vn.EV(recs[j]) == e for j in idx) for e in evs}; w = {j: 1 / cnt[vn.EV(recs[j])] for j in idx}
    # 회귀: 출력 0 B3 = 원문 규칙(끝값 0.02 안쪽)과 LP_V 차이를 기록한다
    z0 = ResF(mlp(13).state_dict(), 13); j0 = idx[0]
    _, mz = evaluate((0, recs[j0], z0, None)); m0 = np.load(os.path.join(ORACLE, f'rec_{j0:02d}.npz'))['m0']
    log(f'{name} 시작 (갱신 {upd}회, 학습률 {lr}): {len(idx)}쌍 {len(evs)}사건, 출력 0 대 LP_V 상대차 최대 {np.abs(mz / m0 - 1).max():.4f} ({recs[j0][0]})', logp)
    res, info, futs = {}, {}, []
    tag = lambda nf, sd: ('B3LIN_' if arch == 'lin' else 'B3_') + f'{nf}' + (f'_s{sd}' if sd else '')
    fname = lambda nf, sd, fi: f'fold_{nf}_' + (f's{sd}_' if sd else '') + f'{fi:02d}.json'
    for sd in seeds:
        for nf in nfs:
            for fi, e in enumerate(evs):
                fp = os.path.join(outdir, fname(nf, sd, fi))
                if os.path.exists(fp):
                    r = json.load(open(fp, encoding='utf-8')); res.update({(tag(nf, sd), int(j)): np.array(v) for j, v in r['res'].items()})
                    info[f'{tag(nf, sd)}_{e}'] = r['info']; continue
                A2 = {j: a2_series(recs[j], a2_weights(D, recs, e)) for j in idx} if nf == 15 else {j: None for j in idx}
                tr = [j for j in idx if vn.EV(recs[j]) != e]; te = [j for j in idx if vn.EV(recs[j]) == e]
                futs.append(ex.submit(b3_fold, (nf, fi, e, recs, tr, te, w, {j: SS[j] for j in tr}, A2, 3 if SMOKE else upd, lr, sd, arch)))
    for fu in as_completed(futs):
        nf, fi, e, sd, r, inf = fu.result()
        json.dump(dict(res={str(j): v for j, v in r.items()}, info=inf), open(os.path.join(outdir, fname(nf, sd, fi)), 'w', encoding='utf-8'))
        res.update({(tag(nf, sd), j): np.array(v) for j, v in r.items()}); info[f'{tag(nf, sd)}_{e}'] = inf
        log(f'겹 {tag(nf, sd)} {e}: {inf}', logp)
    models = [tag(nf, sd) for sd in seeds for nf in nfs]
    if name in ('b3s', 'b3lin'):  # 계획 15.2·16: 신경망 결과(b3l 시드 0, b3s 시드 1·2)를 읽어 3시드 평균 행을 만든다. 지표 개선은 지표에 선형이라 지표 평균 = 개선 평균
        refs = [('b3l', 'fold_13_', 'B3_13')] + ([('b3s', 'fold_13_s1_', 'B3_13_s1'), ('b3s', 'fold_13_s2_', 'B3_13_s2')] if name == 'b3lin' else [])
        for dn, pre, mt in refs:
            dd = os.path.join(OUTROOT, dn + ('_smoke' if SMOKE else ''))
            for fp in (os.listdir(dd) if os.path.isdir(dd) else []):
                if fp.startswith(pre) and fp.endswith('.json') and fp[len(pre):-5].isdigit():
                    res.update({(mt, int(j)): np.array(v) for j, v in json.load(open(os.path.join(dd, fp), encoding='utf-8'))['res'].items()})
        nn3 = ('B3_13', 'B3_13_s1', 'B3_13_s2')
        if all((m, j) in res for m in nn3 for j in idx):
            for j in idx: res[('B3_13_mean3', j)] = np.mean([res[(m, j)] for m in nn3], 0)
            models += (['B3_13', 'B3_13_mean3'] if name == 'b3s' else list(nn3) + ['B3_13_mean3'])
        vf = [v for v in info.values() if 'val_first' in v]
        info['val_summary'] = dict(n=len(vf), n_down=int(sum(v['val_last'] < v['val_first'] for v in vf)),
                                   first_mean=float(np.mean([v['val_first'] for v in vf])) if vf else None, last_mean=float(np.mean([v['val_last'] for v in vf])) if vf else None)
        log(f'고정 검증 손실: {info["val_summary"]}', logp)
    out = summarize(f'{name.upper()} 역전파 학습 수정판 (갱신 {upd}회, 학습률 {lr}, 시드 {seeds}, 정책 {arch})', recs, idx, res, tuple(models), outdir, logp, dict(updates=upd, lr=lr, fold_info=info, minutes=(time.time() - t0) / 60))
    if name == 'b3lin':  # 계획 16: 신경망 − 선형 (사건별 차이, 사건 bootstrap 95% 구간)
        L = ['', '| 신경망 − 선형 | 사건 평균 %p | 95% 구간 | 신경망이 나은/못한 사건 |', '|---|---|---|---|']
        out['nn_minus_lin'] = {}
        for mn in [m for m in ('B3_13', 'B3_13_mean3') if m in out]:
            evs_ = sorted(out[mn]['per_event']); dd = np.array([out[mn]['per_event'][e] - out['B3LIN_13']['per_event'][e] for e in evs_])
            ci = rs.boot_ci(dd) if len(dd) > 1 else [0.0, 0.0]
            out['nn_minus_lin'][mn] = dict(mean=float(dd.mean()), ci95=ci, better=int((dd > 0).sum()), worse=int((dd < 0).sum()))
            L.append(f'| {mn} − B3LIN_13 | {dd.mean():+.2f} | [{ci[0]:+.2f}, {ci[1]:+.2f}] | {(dd > 0).sum()}/{(dd < 0).sum()} |')
        vf = [v for v in info.values() if isinstance(v, dict) and 'val_first' in v]
        L.append(f'\n고정 검증 손실(선형): 끝 < 처음인 겹 {sum(v["val_last"] < v["val_first"] for v in vf)}/{len(vf)}')
        open(os.path.join(outdir, '결과_자동요약.md'), 'a', encoding='utf-8').write('\n'.join(L) + '\n')
        json.dump(out, open(os.path.join(outdir, 'result.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1); log('\n'.join(L), logp)
    finish(name.upper(), outdir, logp, out, tuple(models), t0)


def part_full(recs, ex, t0, seeds=(0, 1, 2)):
    """계획 17: B3_13 설정(b3l)으로 62쌍 전체를 학습해 가중치만 저장한다. 성적은 재지 않는다. 겹 번호 자리에 19를 쓴다."""
    outdir = os.path.join(OUTROOT, 'full' + ('_smoke' if SMOKE else '')); os.makedirs(outdir, exist_ok=True); logp = os.path.join(outdir, 'run.log')
    if os.path.exists(os.path.join(outdir, 'DONE')): log('full 이미 완료', logp); return
    idx = list(range(len(recs)))
    if SMOKE: idx = sorted(idx, key=lambda j: os.path.getsize(recs[j][3]))[:4]
    os.makedirs(vn.CACHE, exist_ok=True)
    list(ex.map(vn.build, [(j, recs[j]) for j in idx if not os.path.exists(os.path.join(vn.CACHE, f'{j}.npz'))]))
    SS = dict(ex.map(start_states, idx)); evs = sorted({vn.EV(recs[j]) for j in idx})
    cnt = {e: sum(vn.EV(recs[j]) == e for j in idx) for e in evs}; w = {j: 1 / cnt[vn.EV(recs[j])] for j in idx}
    FI = 19; log(f'full 시작: {len(idx)}쌍 {len(evs)}사건, 시드 {seeds}, 겹 번호 자리 {FI}', logp)
    futs = [ex.submit(b3_fold, (13, FI, 'ALL', recs, idx, [], w, SS, {j: None for j in idx}, 3 if SMOKE else 1000, 1e-2, sd, 'mlp'))
            for sd in seeds if not os.path.exists(os.path.join(outdir, f'B3_13_full_s{sd}.json'))]
    for fu in as_completed(futs):
        _, _, _, sd, _, inf = fu.result()
        json.dump(inf, open(os.path.join(outdir, f'B3_13_full_s{sd}.json'), 'w', encoding='utf-8')); log(f'full 시드 {sd}: {inf["minutes"]:.0f}분', logp)
    open(os.path.join(outdir, 'DONE'), 'w').write(time.strftime('%Y-%m-%d %H:%M:%S'))
    if SMOKE: log('smoke: 커밋·알림 생략', logp); return
    rel = os.path.relpath(outdir, REPO); fs = [os.path.join(rel, f'B3_13_full_s{sd}.json') for sd in seeds] + [os.path.join(rel, n) for n in ('run.log', 'DONE')]
    msg = f'10주차 17절 62쌍 전체 학습·동결(자동): B3_13 시드 {seeds} 가중치 저장'
    git_commit(fs, msg, logp); notify(msg + f' ({(time.time() - t0) / 60:.0f}분)', logp)


def main():
    global SMOKE
    ap = argparse.ArgumentParser(); ap.add_argument('part', choices=['imit', 'b3', 'b3l', 'b3l15', 'b3s', 'b3lin', 'full', 'all']); ap.add_argument('--smoke', action='store_true')
    A = ap.parse_args(); SMOKE = A.smoke; low_priority(); os.makedirs(OUTROOT, exist_ok=True); logp = os.path.join(OUTROOT, 'run.log')
    recs = recs62(); assert not ({r[0] for r in recs} & {r[0] for r in rs.record_list('test2')})
    # 지진 AI 겹(전체 이름)과 밸브 겹(첫 단어)이 같은 사건 나눔인지 확인
    pairs = {(ga.event_name(r), vn.EV(r)) for r in recs}; assert len(pairs) == len({p[0] for p in pairs}) == len({p[1] for p in pairs}) == 19, pairs
    cache = os.path.join(HERE, 'results_ground_ai', 'data.npz')
    z = np.load(cache, allow_pickle=True); D = tuple(z[k] for k in ('X', 'Y', 'P', 'E', 'R'))
    t0 = time.time(); log(f'시작 {A.part}' + (' (smoke)' if SMOKE else ''), logp)
    try:
        with ProcessPoolExecutor(max_workers=int(os.environ.get('WORKERS', 14))) as ex:
            if A.part in ('imit', 'all'): part_imit(recs, ex, D, time.time())
            if A.part in ('b3', 'all'): part_b3(recs, ex, D, time.time())
            if A.part in ('b3l', 'all'): part_b3(recs, ex, D, time.time(), 'b3l', 1000, 1e-2, (13,))  # 11/12: 계산 시간 때문에 입력 13만 (계획 14.1)
            if A.part == 'b3l15': part_b3(recs, ex, D, time.time(), 'b3l15', 1000, 1e-2, (15,))  # 계획 14.2, all에는 넣지 않음
            if A.part == 'b3s': part_b3(recs, ex, D, time.time(), 'b3s', 1000, 1e-2, (13,), (1, 2))  # 계획 15.2 시드 반복 + 고정 검증 손실
            if A.part == 'full': part_full(recs, ex, time.time())  # 계획 17 62쌍 전체 학습·동결
            if A.part == 'b3lin': part_b3(recs, ex, D, time.time(), 'b3lin', 1000, 1e-2, (13,), (0,), 'lin')  # 계획 16 선형 정책 대조
        log(f'끝 {A.part} {(time.time() - t0) / 60:.1f}분', logp)
    except Exception as e:
        import traceback; log('오류: ' + traceback.format_exc(), logp)
        if not SMOKE: notify(f'B2/B3 밤 학습 오류: {type(e).__name__}. 다음 예약 시각에 이어서 재시도', logp)
        raise


if __name__ == '__main__':
    torch.set_default_dtype(torch.float64)
    main()
