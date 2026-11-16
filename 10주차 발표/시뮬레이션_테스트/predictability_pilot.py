"""지진 파형 1 s 앞 예측 가능성 빠른 확인 (제어 없음, 개발 62쌍, 사건 빼기)."""
import sys, os, numpy as np
from scipy.signal import butter, lfilter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '9주차 발표', '시뮬레이션_테스트', 'peak_rule'))
import run_set as rs
recs = []
for s in ('paper15', 'dev', 'test', 'week8'): recs += rs.record_list(s)
FS, H, W = 20, 20, 80          # 20 Hz, 1 s 앞, 과거 4 s
def series(a, dt):
    b, c = butter(2, 1.0, fs=1/dt); alp = lfilter(b, c, a)            # A-1: LP 지반 속도의 기울기 = LP 가속도
    b8, c8 = butter(2, 8.0, fs=1/dt); a8 = lfilter(b8, c8, a)          # 원파형(8 Hz 앤티에일리어싱)
    k = int(round(1/(dt*FS))); n2 = int(round(2/dt))
    env = np.sqrt(np.convolve(a**2, np.ones(n2)/n2)[:len(a)])          # A-2: 인과 2 s RMS
    return {'raw': a8[::k], 'A1': alp[::k], 'A2': env[::k]}
data = {}
for r in recs:
    ax, ay, dt = rs.load(r)
    for comp, a in (('x', ax), ('y', ay)):
        for key, v in series(a, dt).items(): data.setdefault(key, []).append((r[1].replace(',', '').strip(), v))
def windows(v, key):
    X, Y, P = [], [], []
    thr = 0.05 * (np.abs(v).max() if key != 'A2' else v.max())
    for t in range(W, len(v) - H, 2):                                  # 0.1 s 격자
        hist = v[t-W+1:t+1]
        if key == 'A2':
            y = v[t+H] - v[t]; p = v[t] - v[t-H]; ref = v[t]
        else:
            y = v[t+H]; p = v[t]; ref = np.abs(hist).max()
        if ref < thr: continue
        X.append(hist / (np.abs(hist).max() + 1e-12)); s = np.abs(hist).max() + 1e-12
        Y.append(y / s); P.append(p / s)
    return np.array(X), np.array(Y), np.array(P)
for key in ("raw", "A1", "A2"):
    ev = np.array([e for e, _ in data[key]]); per = [windows(v, key) for _, v in data[key]]
    out = {m: [] for m in ('persist', 'linear')}; Ys = []
    for e in np.unique(ev):
        tr = [per[i] for i in range(len(per)) if ev[i] != e]; te = [per[i] for i in range(len(per)) if ev[i] == e]
        Xtr = np.vstack([p[0] for p in tr]); Ytr = np.concatenate([p[1] for p in tr])
        A = np.c_[Xtr, np.ones(len(Xtr))]; w = np.linalg.solve(A.T @ A + 1e-2*np.eye(A.shape[1]), A.T @ Ytr)
        Xte = np.vstack([p[0] for p in te]); Yte = np.concatenate([p[1] for p in te]); Pte = np.concatenate([p[2] for p in te])
        Ys.append(Yte); out['persist'].append(Pte); out['linear'].append(np.c_[Xte, np.ones(len(Xte))] @ w)
    Y = np.concatenate(Ys); mz = np.mean(Y**2)
    print(f"[{key}] windows={len(Y)}")
    for m, l in out.items():
        p = np.concatenate(l); skill = 1 - np.mean((Y-p)**2)/mz
        big = np.abs(Y) > np.median(np.abs(Y))
        print(f"  {m:8s} skill vs zero={skill:+.3f}  corr={np.corrcoef(Y,p)[0,1]:+.3f}  sign acc={np.mean(np.sign(p)==np.sign(Y)):.3f}  sign acc(|y| big)={np.mean(np.sign(p[big])==np.sign(Y[big])):.3f}")
        up = Y > 0
        print(f"    rising share={up.mean():.3f}  recall(rising)={np.mean(p[up]>0):.3f}  precision(pred rising)={np.mean(Y[p>0]>0):.3f}")
