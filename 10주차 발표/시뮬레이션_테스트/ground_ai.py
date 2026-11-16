"""10주차 A0a: 지진 파형 1 s 뒤 기울기 예측 (제어 없음). 설정은 10주차_계획.md 4절·11절에서 실행 전에 고정.

대상 (성분 X·Y 각각, 20 Hz 격자):
  A1 = 1 Hz 저역통과 지반 가속도의 1 s 뒤 값 (= 저역통과 지반 속도의 기울기)
  A2 = 2 s 이동 RMS 세기의 1 s 변화 (env[t+1 s] - env[t])
예측기: zero, persist, AR_IMS(창마다 AR(20) 적합 후 20스텝 재귀), LIN_SELF(자기 이력 80점 → 직접),
        LIN_ALL(신경망과 같은 입력 → 직접), MLP(2층 32노드, 시드 3개 예측 평균).
검증: 개발 62쌍 19사건, 사건 하나씩 빼기. test·test2는 쓰지 않는다.

실행:  python ground_ai.py            (본 실행, 끝나면 결과 커밋·push·알림)
       python ground_ai.py --smoke    (겹 2개, epoch 5, 시간 측정용, 커밋·알림 없음)
다시 실행하면 끝난 겹은 건너뛴다(results_ground_ai/fold_XX.npz).
"""
import sys, os, json, time, argparse, subprocess, urllib.request
import numpy as np
from scipy.signal import butter, lfilter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, '9주차 발표', '시뮬레이션_테스트', 'peak_rule'))
import run_set as rs  # noqa: E402
import torch  # noqa: E402

FS, H, W, STEP = 20, 20, 80, 2           # 20 Hz, 1 s 앞, 과거 4 s, 0.1 s 격자
SEEDS = (0, 1, 2)
TARGETS = ('A1x', 'A1y', 'A2x', 'A2y')
torch.set_num_threads(8)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log(msg, path):
    line = time.strftime('%Y-%m-%d %H:%M:%S ') + msg
    print(line, flush=True)
    with open(path, 'a', encoding='utf-8') as f: f.write(line + '\n')


def series(a, dt):
    """원신호 → 20 Hz 격자의 (a8, alp, env). 필터는 모두 인과."""
    b, c = butter(2, 8.0, fs=1 / dt); a8 = lfilter(b, c, a)
    b, c = butter(2, 1.0, fs=1 / dt); alp = lfilter(b, c, a)
    n2 = int(round(2 / dt)); env = np.sqrt(np.convolve(a ** 2, np.ones(n2) / n2)[:len(a)])
    t = np.arange(len(a)) * dt; tg = np.arange(0, t[-1], 1 / FS)
    return [np.interp(tg, t, v) for v in (a8, alp, env)]


def event_name(rec):
    """같은 지진의 표기 차이를 합친다 ('Chi-Chi Taiwan' = 'Chi-Chi, Taiwan', 'Kobe Japan' = 'Kobe, Japan')."""
    return rec[1].replace(',', '').strip()


def build(recs):
    """창 단위 자료. X: [a8x,a8y,alpx,alpy,envx,envy] 각 80점(창 최대 |a8|로 나눔)."""
    X, Y, P, E, R = [], [], [], [], []
    for ri, rec in enumerate(recs):
        ax, ay, dt = rs.load(rec)
        (a8x, lpx, evx), (a8y, lpy, evy) = series(ax, dt), series(ay, dt)
        n = min(len(a8x), len(a8y)); emax = max(evx[:n].max(), evy[:n].max())
        for t in range(W - 1, n - H, STEP):
            if max(evx[t], evy[t]) < 0.05 * emax: continue
            sl = slice(t - W + 1, t + 1)
            s = max(np.abs(a8x[sl]).max(), np.abs(a8y[sl]).max()) + 1e-12
            X.append(np.concatenate([a8x[sl], a8y[sl], lpx[sl], lpy[sl], evx[sl], evy[sl]]) / s)
            Y.append(np.array([lpx[t + H], lpy[t + H], evx[t + H] - evx[t], evy[t + H] - evy[t]]) / s)
            P.append(np.array([lpx[t], lpy[t], evx[t] - evx[t - H], evy[t] - evy[t - H]]) / s)
            E.append(event_name(rec)); R.append(ri)
    return np.array(X, np.float32), np.array(Y), np.array(P), np.array(E), np.array(R)


def self_hist(X, j):
    """대상 j의 자기 이력 80점 (A1x→alpx, A1y→alpy, A2x→envx, A2y→envy)."""
    blk = (2, 3, 4, 5)[j]
    return X[:, blk * W:(blk + 1) * W].astype(float)


def ar_ims(hist, is_env, order=20):
    """창마다 AR(order) 최소제곱 적합, H스텝 재귀. ponytail: 창별 lstsq 반복, 느리면 배치화."""
    out = np.empty(len(hist))
    for i, h in enumerate(hist):
        A = np.lib.stride_tricks.sliding_window_view(h[:-1], order); b = h[order:]
        w = np.linalg.solve(A.T @ A + 1e-3 * np.trace(A.T @ A) / order * np.eye(order) + 1e-12 * np.eye(order), A.T @ b)
        buf = list(h[-order:])
        for _ in range(H): buf.append(float(np.dot(w, buf[-order:])))
        lim = 10 * np.abs(h).max() + 1e-12
        y = float(np.clip(buf[-1], -lim, lim))
        out[i] = y - h[-1] if is_env else y
    return out


def ridge(Xtr, ytr, Xte, lam=1e-2):
    A = np.c_[Xtr, np.ones(len(Xtr))]
    w = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ ytr)
    return np.c_[Xte, np.ones(len(Xte))] @ w


def mlp(Xtr, Ytr, Xva, Yva, Xte, seed, max_epochs):
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    mu, sd = Ytr.mean(0), Ytr.std(0) + 1e-12
    net = torch.nn.Sequential(torch.nn.Linear(Xtr.shape[1], 32), torch.nn.ReLU(),
                              torch.nn.Linear(32, 32), torch.nn.ReLU(), torch.nn.Linear(32, Ytr.shape[1]))
    opt = torch.optim.Adam(net.parameters(), 1e-3)
    xt = torch.tensor(Xtr); yt = torch.tensor(((Ytr - mu) / sd).astype(np.float32))
    xv = torch.tensor(Xva); yv = torch.tensor(((Yva - mu) / sd).astype(np.float32))
    best, best_state, bad, ep = np.inf, None, 0, 0
    for ep in range(max_epochs):
        net.train()
        for idx in np.array_split(rng.permutation(len(xt)), max(1, len(xt) // 256)):
            opt.zero_grad(); loss = torch.mean((net(xt[idx]) - yt[idx]) ** 2); loss.backward(); opt.step()
        net.eval()
        with torch.no_grad(): v = float(torch.mean((net(xv) - yv) ** 2))
        if v < best - 1e-6: best, best_state, bad = v, {k: x.clone() for k, x in net.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= 10: break
    net.load_state_dict(best_state); net.eval()
    with torch.no_grad(): pred = net(torch.tensor(Xte)).numpy() * sd + mu
    return pred, ep + 1, best


def run_fold(k, ev_test, D, max_epochs):
    X, Y, P, E, R = D
    te = E == ev_test; trall = ~te
    tr_events = sorted(set(E[trall]))
    val_ev = set(np.random.default_rng(1000 + k).choice(tr_events, 3, replace=False))
    va = trall & np.isin(E, list(val_ev)); tr = trall & ~va
    out = {'idx': np.where(te)[0]}
    out['zero'] = np.zeros((te.sum(), 4)); out['persist'] = P[te]
    out['AR_IMS'] = np.stack([ar_ims(self_hist(X[te], j), j >= 2) for j in range(4)], 1)
    out['LIN_SELF'] = np.stack([ridge(self_hist(X[trall], j), Y[trall, j], self_hist(X[te], j)) for j in range(4)], 1)
    out['LIN_ALL'] = ridge(X[trall].astype(float), Y[trall], X[te].astype(float))
    preds, info = [], []
    for s in SEEDS:
        p, ep, vb = mlp(X[tr], Y[tr], X[va], Y[va], X[te], s, max_epochs); preds.append(p); info.append((ep, vb))
    out['MLP'] = np.mean(preds, 0); out['mlp_info'] = np.array(info)
    return out


def boot(d, n=10000, seed=8500):
    rng = np.random.default_rng(seed); m = rng.choice(d, (n, len(d))).mean(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def evaluate(D, folds):
    X, Y, P, E, R = D
    idx = np.concatenate([f['idx'] for f in folds])
    methods = ('zero', 'persist', 'AR_IMS', 'LIN_SELF', 'LIN_ALL', 'MLP')
    pred = {m: np.vstack([f[m] for f in folds]) for m in methods}
    Yt, Et = Y[idx], E[idx]; events = sorted(set(Et)); res = {}
    for name, cols in (('A1', [0, 1]), ('A2', [2, 3])):
        y = Yt[:, cols].ravel(); ev = np.repeat(Et, 2)
        r = {'n_windows': int(len(y))}
        for m in methods:
            p = pred[m][:, cols].ravel(); big = np.abs(y) > np.median(np.abs(y))
            ev_skill = [1 - np.mean((y[ev == e] - p[ev == e]) ** 2) / np.mean(y[ev == e] ** 2) for e in events]
            d = {'skill_pooled': float(1 - np.mean((y - p) ** 2) / np.mean(y ** 2)),
                 'skill_event_mean': float(np.mean(ev_skill)), 'skill_event': dict(zip(events, map(float, ev_skill))),
                 'corr': float(np.corrcoef(y, p)[0, 1]) if p.std() > 0 else 0.0,
                 'sign_acc': float(np.mean(np.sign(p) == np.sign(y))), 'sign_acc_big': float(np.mean(np.sign(p[big]) == np.sign(y[big])))}
            if name == 'A2':
                up = y > 0
                d['rising_recall'] = float(np.mean(p[up] > 0))
                d['rising_precision'] = float(np.mean(y[p > 0] > 0)) if (p > 0).any() else 0.0
            r[m] = d
        base = max(('persist', 'AR_IMS', 'LIN_SELF', 'LIN_ALL'), key=lambda m: r[m]['skill_event_mean'])
        diff = np.array([r['MLP']['skill_event'][e] - r[base]['skill_event'][e] for e in events])
        ci = boot(diff)
        r['verdict'] = {'best_baseline': base, 'mlp_minus_best_event_mean': float(diff.mean()), 'ci95': ci,
                        'events_better': int((diff > 0).sum()), 'events_worse': int((diff < 0).sum()),
                        'adopt': bool(diff.mean() > 0 and ci[0] > 0 and (diff > 0).sum() > (diff < 0).sum())}
        res[name] = r
    return res


def summary_md(res, folds, elapsed):
    L = ['# 10주차 A0a 결과: 지진 파형 1 s 뒤 기울기 예측 (자동 생성)', '',
         f'- 생성 {time.strftime("%Y-%m-%d %H:%M")}, 계산 {elapsed / 60:.1f}분, 겹 {len(folds)}개(사건 빼기), MLP 시드 {len(SEEDS)}개 예측 평균',
         '- skill = 1 − MSE/MSE(zero). 사건 평균은 사건별 skill의 평균.', '']
    for name, title in (('A1', 'A1 저역통과 지반 속도 기울기'), ('A2', 'A2 세기(2 s RMS) 1 s 변화')):
        r = res[name]; L += [f'## {title} (창 {r["n_windows"]}개)', '',
                             '| 예측기 | skill(전체) | skill(사건 평균) | 상관 | 부호 정답 | 부호 정답(큰 값) |' + (' 상승 정밀도 | 상승 재현율 |' if name == 'A2' else ''),
                             '|---|---|---|---|---|---|' + ('---|---|' if name == 'A2' else '')]
        for m in ('persist', 'AR_IMS', 'LIN_SELF', 'LIN_ALL', 'MLP'):
            d = r[m]; row = f'| {m} | {d["skill_pooled"]:+.3f} | {d["skill_event_mean"]:+.3f} | {d["corr"]:+.3f} | {d["sign_acc"]:.3f} | {d["sign_acc_big"]:.3f} |'
            if name == 'A2': row += f' {d["rising_precision"]:.3f} | {d["rising_recall"]:.3f} |'
            L.append(row)
        v = r['verdict']
        L += ['', f'- MLP − 최선 기준({v["best_baseline"]}) 사건 평균 skill 차: {v["mlp_minus_best_event_mean"]:+.4f} [{v["ci95"][0]:+.4f}, {v["ci95"][1]:+.4f}], '
                  f'나아진 사건 {v["events_better"]}, 나빠진 사건 {v["events_worse"]} → **{"채택" if v["adopt"] else "불채택"}** (사전 기준)', '']
    ep = np.vstack([f['mlp_info'] for f in folds])[:, 0]
    L.append(f'- MLP 종료 epoch: 중앙값 {np.median(ep):.0f}, 범위 {ep.min():.0f}~{ep.max():.0f}')
    return '\n'.join(L) + '\n'


def notify(msg, logp):
    topic_file = os.path.join(os.path.expanduser('~'), '.ntfy_topic')
    if not os.path.exists(topic_file): log('알림 생략: ~/.ntfy_topic 없음', logp); return
    topic = open(topic_file, encoding='utf-8').read().strip()
    try:
        req = urllib.request.Request(f'https://ntfy.sh/{topic}', data=msg.encode('utf-8'), headers={'Title': 'TLCD AI'})
        urllib.request.urlopen(req, timeout=20); log('알림 보냄', logp)
    except Exception as e: log(f'알림 실패: {e}', logp)


def git_commit(paths, msg, logp):
    try:
        subprocess.run(['git', '-C', REPO, 'add', *paths], check=True, capture_output=True)
        subprocess.run(['git', '-C', REPO, 'commit', '-m', msg + '\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_018WYuHT2aPry7q1fvqT5VgR', '--', *paths], check=True, capture_output=True)
        subprocess.run(['git', '-C', REPO, 'push'], check=True, capture_output=True, timeout=120); log('커밋·push 완료', logp)
    except Exception as e: log(f'git 실패: {e}', logp)


def low_priority():
    """사용자 작업을 방해하지 않게 Windows 우선순위를 '보통 아래'로 낮춘다."""
    if os.name == 'nt':
        import ctypes
        k = ctypes.windll.kernel32; k.GetCurrentProcess.restype = ctypes.c_void_p  # 64비트 핸들 -1이 잘리지 않게 (11/13: 이전엔 오류 6으로 둘 다 실패)
        k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]; k.SetProcessInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong]
        k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
        # 11/13: 작업 스케줄러(창 없음)로 띄우면 Windows가 EcoQoS로 E코어 4개에만 몰아 넣어 3배 느려졌다. 실행 속도 제한을 끈다
        class PPT(ctypes.Structure): _fields_ = [('Version', ctypes.c_ulong), ('ControlMask', ctypes.c_ulong), ('StateMask', ctypes.c_ulong)]
        st = PPT(1, 1, 0); k.SetProcessInformation(k.GetCurrentProcess(), 4, ctypes.byref(st), ctypes.sizeof(st))


def main():
    low_priority()
    ap = argparse.ArgumentParser(); ap.add_argument('--smoke', action='store_true'); a = ap.parse_args()
    outdir = os.path.join(HERE, 'results_ground_ai' + ('_smoke' if a.smoke else '')); os.makedirs(outdir, exist_ok=True)
    logp = os.path.join(outdir, 'run.log'); done_flag = os.path.join(outdir, 'DONE')
    if os.path.exists(done_flag): log('이미 완료됨, 종료', logp); return
    t0 = time.time(); log('시작' + (' (smoke)' if a.smoke else ''), logp)
    try:
        cache = os.path.join(outdir, 'data.npz')
        if os.path.exists(cache):
            z = np.load(cache, allow_pickle=True); D = tuple(z[k] for k in ('X', 'Y', 'P', 'E', 'R'))
        else:
            recs = []
            for s in ('paper15', 'dev', 'test', 'week8'): recs += rs.record_list(s)
            D = build(recs); np.savez(cache, X=D[0], Y=D[1], P=D[2], E=D[3], R=D[4])
        events = sorted(set(D[3])); log(f'자료: 창 {len(D[0])}개, 사건 {len(events)}개, 입력 {D[0].shape[1]}', logp)
        if a.smoke: events = events[:2]
        folds = []
        for k, e in enumerate(events):
            fp = os.path.join(outdir, f'fold_{k:02d}.npz')
            if os.path.exists(fp):
                folds.append(dict(np.load(fp, allow_pickle=True))); continue
            tk = time.time(); f = run_fold(k, e, D, 5 if a.smoke else 300)
            np.savez(fp, **f); folds.append(f)
            log(f'겹 {k + 1}/{len(events)} {e}: {time.time() - tk:.0f}s, MLP epoch {f["mlp_info"][:, 0].tolist()}', logp)
        if a.smoke: log(f'smoke 끝 {time.time() - t0:.0f}s', logp); return
        res = evaluate(D, folds)
        json.dump(res, open(os.path.join(outdir, 'result_ground_ai.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        md = summary_md(res, folds, time.time() - t0)
        open(os.path.join(outdir, '결과_자동요약.md'), 'w', encoding='utf-8').write(md)
        open(done_flag, 'w').write(time.strftime('%Y-%m-%d %H:%M:%S'))
        log('완료', logp)
        v1, v2 = res['A1']['verdict'], res['A2']['verdict']
        rel = os.path.relpath(outdir, REPO)
        git_commit([os.path.join(rel, n) for n in ('result_ground_ai.json', '결과_자동요약.md', 'run.log', 'DONE')],
                   f'10주차 A0a 결과(자동): 지진 AI A1 {"채택" if v1["adopt"] else "불채택"}, A2 {"채택" if v2["adopt"] else "불채택"}', logp)
        notify(f'지진 AI 학습 완료. A1 MLP-{v1["best_baseline"]} {v1["mlp_minus_best_event_mean"]:+.3f}, '
               f'A2 MLP-{v2["best_baseline"]} {v2["mlp_minus_best_event_mean"]:+.3f}. 결과_자동요약.md', logp)
    except Exception as e:
        import traceback; log('오류: ' + traceback.format_exc(), logp)
        if not a.smoke: notify(f'지진 AI 학습 오류: {type(e).__name__}. 다음 예약 시각에 이어서 재시도', logp)
        raise


if __name__ == '__main__':
    main()
