"""공동 후보 점수망 학습 (8주차 v2 계획 §6.3).

입력: scripts/generate_joint_teacher.m 의 CSV (행 = 상태 x 후보, 특징 98열 x01..x98)
목표: y = J_true / J_true(R) - 1  (같은 상태의 R 후보 대비 상대 비용, 실제 미래로 모의한 비인과 teacher)
망  : 98 -> FC128/ReLU -> FC64/ReLU -> 1, Huber, Adam 1e-3, batch 128, 최대 50 epoch, 검증 손실 5회 연속 개선 없으면 종료, seed 8401
지표 (느린 결정 상태, 실제 미래 기준 만족 = Qc <= QR(1+tol) & Mc <= MR(1+tol), R 항상 만족):
  top3_hit      : 공동 후보(유지·R 제외) 중 만족 최선이 점수망 top 3 안에 있는 비율
  eval_hit      : 전체 만족 최선이 물리 검사 집합(top 3 + 유지 + R) 안에 있는 비율
  regret        : (검사 집합 만족 최선 J - 전체 만족 최선 J) / J_R 평균
  fallback      : top 3가 모두 불만족(실제 미래)인 비율 -> 유지·R로 돌아감
  random_top3   : 같은 지표를 무작위 3개로 (기준선, 고정 시드 1000회 평균)
출력: <out>.json (가중치·표준화·지표·학습 곡선·일치 확인용 표본), <out>.pt
"""
import argparse, json, time, hashlib
import numpy as np
import torch
import torch.nn as nn

TOL = 1e-12


def load(path):
    with open(path, encoding='utf-8') as f:
        hdr = f.readline().strip().split(',')
    D = np.loadtxt(path, delimiter=',', skiprows=1, ndmin=2)
    col = {h: i for i, h in enumerate(hdr)}
    X = D[:, [col[h] for h in hdr if h.startswith('x') and h[1:].isdigit()]]
    return D, col, X


def targets(D, col):
    st = D[:, col['state']].astype(int)
    J = D[:, col['J_true']]
    isR = D[:, col['isR']] > 0.5
    JR = np.full(D.shape[0], np.nan)
    for s in np.unique(st):
        m = st == s
        r = np.where(m & isR)[0]
        if len(r):
            JR[m] = J[r[0]]
    y = J / JR - 1.0
    feas = (D[:, col['Qc_true']] <= D[:, col['QR_true']] * (1 + TOL)) & (D[:, col['Mc_true']] <= D[:, col['MR_true']] * (1 + TOL)) & np.isfinite(J)
    feas[isR] = np.isfinite(J[isR])
    return st, y, JR, feas


def metrics(D, col, st, y, JR, feas, score, mask, rng=None, k=3):
    """mask: 행 선택 (분할), 느린 결정 상태만."""
    kind = D[:, col['kind']]
    isR = D[:, col['isR']] > 0.5
    isH = D[:, col['isHold']] > 0.5
    J = D[:, col['J_true']]
    out = dict(n=0, top3_hit=0.0, eval_hit=0.0, regret=0.0, fallback=0.0)
    vals = []
    for s in np.unique(st[mask & (kind == 1)]):
        m = np.where((st == s) & mask)[0]
        if not np.isfinite(JR[m[0]]) or JR[m[0]] <= 0:
            continue
        pool = m[~isR[m] & ~isH[m] & np.isfinite(J[m])]
        if len(pool) == 0:
            continue
        if rng is None:
            top = pool[np.argsort(score[pool], kind='stable')[:k]]
        else:
            top = rng.choice(pool, size=min(k, len(pool)), replace=False)
        fp = pool[feas[pool]]
        allf = m[feas[m]]
        best_all = allf[np.argmin(J[allf])]
        ev = np.concatenate([top, m[isR[m] | isH[m]]])
        evf = ev[feas[ev]]
        best_ev = evf[np.argmin(J[evf])]
        hit = 1.0 if (len(fp) and fp[np.argmin(J[fp])] in top) else (np.nan if len(fp) == 0 else 0.0)
        vals.append((hit, float(best_all == best_ev or J[best_ev] <= J[best_all]), (J[best_ev] - J[best_all]) / JR[m[0]], float(not feas[top].any())))
    if not vals:
        return out
    v = np.array(vals, dtype=float)
    out = dict(n=len(v), top3_hit=float(np.nanmean(v[:, 0])), n_top3_defined=int(np.sum(np.isfinite(v[:, 0]))),
               eval_hit=float(v[:, 1].mean()), regret=float(v[:, 2].mean()), fallback=float(v[:, 3].mean()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--epochs', type=int, default=50)
    ap.add_argument('--patience', type=int, default=5)
    ap.add_argument('--batch', type=int, default=128)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--seed', type=int, default=8401)
    ap.add_argument('--device', default='cpu')
    a = ap.parse_args()
    torch.manual_seed(a.seed); np.random.seed(a.seed)
    dev = torch.device('cuda' if (a.device == 'auto' and torch.cuda.is_available()) else ('cpu' if a.device == 'auto' else a.device))
    D, col, X = load(a.data)
    st, y, JR, feas = targets(D, col)
    split = D[:, col['split']].astype(int)
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    tr = ok & (split == 1); va = ok & (split == 2)
    mu = X[tr].mean(0); sd = X[tr].std(0); sd[sd < 1e-9] = 1.0
    Z = (X - mu) / sd
    Z[~np.isfinite(Z)] = 0.0
    net = nn.Sequential(nn.Linear(X.shape[1], 128), nn.ReLU(), nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1)).double().to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=a.lr)
    lossf = nn.HuberLoss()
    Xt = torch.tensor(Z[tr], device=dev); yt = torch.tensor(y[tr], device=dev).unsqueeze(1)
    Xv = torch.tensor(Z[va], device=dev); yv = torch.tensor(y[va], device=dev).unsqueeze(1)
    g = torch.Generator().manual_seed(a.seed)
    best = (np.inf, -1, None); hist = []; bad = 0; t0 = time.time()
    for ep in range(1, a.epochs + 1):
        net.train()
        perm = torch.randperm(Xt.shape[0], generator=g)
        tl = 0.0
        for b in range(0, len(perm), a.batch):
            idx = perm[b:b + a.batch].to(dev)
            opt.zero_grad()
            l = lossf(net(Xt[idx]), yt[idx]); l.backward(); opt.step()
            tl += l.item() * len(idx)
        net.eval()
        with torch.no_grad():
            vl = lossf(net(Xv), yv).item() if Xv.shape[0] else float('nan')
        hist.append(dict(epoch=ep, train=tl / max(1, Xt.shape[0]), val=vl))
        print('epoch %2d train %.5f val %.5f' % (ep, hist[-1]['train'], vl), flush=True)
        if vl < best[0] - 1e-12:
            best = (vl, ep, {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}); bad = 0
        else:
            bad += 1
            if bad >= a.patience:
                break
    net.load_state_dict(best[2])
    net.eval()
    with torch.no_grad():
        score = net(torch.tensor(Z, device=dev)).cpu().numpy().ravel()
    rng = np.random.default_rng(a.seed)
    res = {}
    for nm, m in (('train', tr), ('val', va)):
        res[nm] = metrics(D, col, st, y, JR, feas, score, m)
        rs = [metrics(D, col, st, y, JR, feas, score, m, rng=rng) for _ in range(200)]
        res[nm + '_random'] = {k: float(np.nanmean([r[k] for r in rs if k in r])) for k in ('top3_hit', 'eval_hit', 'regret', 'fallback')}
    sd_ = net.state_dict()
    W = lambda k: sd_[k].cpu().numpy()
    ns = int(min(50, va.sum()))
    vi = np.where(va)[0][:ns]
    sha = hashlib.sha256(open(a.data, 'rb').read()).hexdigest()[:16]
    out = dict(mu=mu.tolist(), sd=sd.tolist(), W1=W('0.weight').tolist(), b1=W('0.bias').tolist(), W2=W('2.weight').tolist(), b2=W('2.bias').tolist(),
               W3=W('4.weight').ravel().tolist(), b3=float(W('4.bias')[0]), best_epoch=best[1], val_loss=best[0], history=hist,
               metrics=res, n_train_rows=int(tr.sum()), n_val_rows=int(va.sum()), n_train_states=int(len(np.unique(st[tr]))), n_val_states=int(len(np.unique(st[va]))),
               seed=a.seed, device=str(dev), train_s=time.time() - t0, data_sha16=sha, torch=torch.__version__,
               target='J_true/J_true(R) - 1', parity_X=X[vi].tolist(), parity_y=score[vi].tolist())
    with open(a.out + '.json', 'w', encoding='utf-8') as f:
        json.dump(out, f)
    torch.save(best[2], a.out + '.pt')
    print(json.dumps(dict(best_epoch=best[1], val_loss=best[0], metrics=res), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
