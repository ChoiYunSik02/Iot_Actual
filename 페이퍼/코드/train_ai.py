# -*- coding: utf-8 -*-
"""진동수 · 회전각 예측 AI 학습과 평가 (`페이퍼/02_AI_학습_계획.md` 4~6절).

입력: 지진 감지 후 T_obs초의 X·Y 지반가속도 → 스펙트럼 64 + 세기 · 방향 4 + 건물 진동수 1 = 69개
출력: Oracle 49칸 점수 지도 (샘플 평균을 뺀 상대 점수) → argmax = 예측 (f, θ)
평가: 실제 기록 11쌍을 하나씩 빼고 학습(그 기록의 변형도 학습에서 뺌) → 뺀 기록에서 시뮬레이션
  preset : 원거리 — 상류 관측소 조기경보로 미리 봤다고 보고 t = 0부터 예측값 (Oracle과 같은 조건)
  online : 근 · 중거리 — 감지 후 T_obs초가 지나서 예측값 지령 (펌프 2.6 s 램프 그대로)
사용: python train_ai.py [--tobs 5] [--epochs 400] [--mode preset online]
"""
import argparse, glob, json, os, time
from multiprocessing import Pool
import numpy as np
import torch
import torch.nn as nn
import rstlcd as R
import records
from gen_labels import DT, F_GRID, TH_GRID, F_RANGE, TAG, OUT as LABEL_DIR

DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
TRIG = 0.005                                     # 감지 문턱 [m/s²] (0.5 gal)
NFFT = 16384                                    # 해상도 0.006 Hz (가장 좁은 칸 0.013 Hz)
BINS = np.geomspace(0.1, 5.0, 33)                # 32칸


# ── 입력 특징 ─────────────────────────────────────────────────
def trigger_index(x, y):
    hit = np.flatnonzero(np.maximum(np.abs(x), np.abs(y)) > TRIG)
    return int(hit[0]) if len(hit) else 0


def features(x, y, k_scale, tobs):
    i0 = trigger_index(x, y); w = slice(i0, i0 + int(tobs / DT))
    wx, wy = x[w], y[w]
    fr = np.fft.rfftfreq(NFFT, DT)
    spec = []
    for v in (wx, wy):
        A = np.abs(np.fft.rfft(v, NFFT))
        spec.append([A[(fr >= lo) & (fr < hi)].mean() for lo, hi in zip(BINS[:-1], BINS[1:])])
    spec = np.log(np.array(spec) + 1e-9); spec -= spec.max()     # 모양만 (세기는 아래에서 따로)
    px, py = np.abs(wx).max() + 1e-9, np.abs(wy).max() + 1e-9
    C = np.cov(np.vstack([wx, wy])); phi = 0.5 * np.arctan2(2 * C[0, 1], C[0, 0] - C[1, 1])   # 주축 방향
    extra = [np.log(px), np.log(py / px), np.sin(2 * phi), np.cos(2 * phi), R.F0 * np.sqrt(k_scale) / R.F0 - 1]
    return np.r_[spec.ravel(), extra].astype(np.float32), i0


# ── 데이터 ───────────────────────────────────────────────────
def load_labels(tobs):
    X, Y, src = [], [], []
    for p in sorted(glob.glob(os.path.join(LABEL_DIR, 's*.npz'))):
        d = np.load(p); m = json.loads(str(d['meta']))
        X.append(features(d['agx'].astype(float), d['agy'].astype(float), m['k_scale'], tobs)[0])
        s = d['score'].ravel(); Y.append(s - s.mean())
        src.append(m['src'] if m['kind'] == 'real' else -1)
    return np.array(X), np.array(Y, np.float32), np.array(src)


def test_records():
    """학습 데이터 변형의 src 번호와 같은 순서 (gen_labels.py의 pool_rec)."""
    return [(f'PEER {no} {st}', x, y) for no, st, x, y in records.paper_pairs(DT)[0]] + records.held_pairs(DT)


# ── 모델 ─────────────────────────────────────────────────────
def make_model(n_in, n_out):
    return nn.Sequential(nn.Linear(n_in, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, n_out))


def train(X, Y, epochs, seed=0):
    torch.manual_seed(seed)
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xt = torch.tensor((X - mu) / sd, device=DEV); Yt = torch.tensor(Y, device=DEV)
    n = len(X); rng = np.random.default_rng(seed); idx = rng.permutation(n); nv = max(1, n // 7)
    va, tr = idx[:nv], idx[nv:]
    model = make_model(X.shape[1], Y.shape[1]).to(DEV)
    opt = torch.optim.AdamW(model.parameters(), 2e-3, weight_decay=1e-3)
    best, best_state = 1e9, None
    for ep in range(epochs):
        model.train()
        for b in np.array_split(rng.permutation(tr), max(1, len(tr) // 128)):
            loss = ((model(Xt[b]) - Yt[b]) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            v = ((model(Xt[va]) - Yt[va]) ** 2).mean().item()
        if v < best:
            best, best_state = v, {k: t.clone() for k, t in model.state_dict().items()}
    model.load_state_dict(best_state)
    return model, mu, sd, best


def predict(model, mu, sd, feat):
    with torch.no_grad():
        s = model(torch.tensor((feat - mu) / sd, device=DEV)[None]).cpu().numpy().reshape(len(F_GRID), len(TH_GRID))
    a, b = np.unravel_index(np.argmax(s), s.shape)
    return float(F_GRID[a]), float(TH_GRID[b])


# ── 시뮬레이션 평가 (CPU 병렬) ─────────────────────────────────
C_SCALE = 30.0


def ai_kw(kw):
    """ai_f · ai_th · t_set → simulate 인자 (람다는 프로세스 사이로 못 넘겨서 작업 프로세스 안에서 만듦)."""
    t_set = kw.pop('t_set', None)
    if 'ai_f' in kw:
        f, th = kw.pop('ai_f'), kw.pop('ai_th')
        if t_set is None:
            kw.update(f0=f, theta0=th, rs_freq=lambda t, s: f, rs_theta=lambda t, s: th)
        else:
            kw.update(rs_freq=lambda t, s: f if t >= t_set else R.F0, rs_theta=lambda t, s: th if t >= t_set else 0.0)
    return kw


def sim(job):
    key, x, y, kw = job
    kw.setdefault('f_range', F_RANGE)
    return key, R.metrics(R.simulate(x, y, DT, c_scale=C_SCALE, **ai_kw(kw)))


def score(red):
    return float(np.mean(list(red.values())))


FIXED = (0.3204, 45.0)      # 원문 ±5% 라벨에서 가장 흔한 칸 (plot_fig4.py용). train_ai는 라벨에서 직접 셈


def baselines(recs, k, workers):
    """실제 기록의 비교군 + Oracle 격자 (건물 강성 배율 k마다 한 번 계산해 저장)."""
    cache = f'results/ai_eval_baselines{TAG}.json' if k == 1.0 else f'results/ai_eval_baselines{TAG}_k{k:g}.json'
    if os.path.exists(cache):
        return {tuple(json.loads(key)): v for key, v in json.load(open(cache, encoding='utf-8')).items()}
    jobs = []
    for r, (name, x, y) in enumerate(recs):
        jobs += [((r, 'E0'), x, y, dict(case='none', k_scale=k)), ((r, 'E1b'), x, y, dict(case='passive', f0=0.3204, k_scale=k)),
                 ((r, 'E2'), x, y, dict(case='rstlcd', k_scale=k))]
        jobs += [((r, 'E4', a, b), x, y, dict(case='rstlcd', ai_f=float(f), ai_th=float(th), k_scale=k))
                 for a, f in enumerate(F_GRID) for b, th in enumerate(TH_GRID)]
    t0 = time.time()
    with Pool(workers) as pool:
        base = dict(pool.map(sim, jobs, chunksize=2))
    json.dump({json.dumps(list(key)): v for key, v in base.items()}, open(cache, 'w', encoding='utf-8'))
    print(f'비교군 · Oracle 격자 계산 (k = {k:g}) {len(jobs)}회, {time.time() - t0:.0f}s', flush=True)
    return base


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--tobs', type=float, nargs='+', default=[5.0])
    ap.add_argument('--mode', nargs='+', default=['preset', 'online'])
    ap.add_argument('--kscale', type=float, nargs='+', default=[1.0], help='시험 건물 강성 배율 (실험 1: 진동수 √k배)')
    ap.add_argument('--epochs', type=int, default=400)
    ap.add_argument('--tag', default='', help='결과 파일 이름 꼬리표')
    ap.add_argument('--workers', type=int, default=max(1, os.cpu_count() - 1))
    args = ap.parse_args()
    print(f'장치: {DEV}' + (f' ({torch.cuda.get_device_name(0)})' if DEV == 'cuda' else ''), flush=True)
    recs = test_records()
    os.makedirs('results', exist_ok=True); os.makedirs('models', exist_ok=True)
    bases = {k: baselines(recs, k, args.workers) for k in args.kscale}

    summary = []
    for tobs in args.tobs:
        X, Y, src = load_labels(tobs)
        fa, fb = np.unravel_index(Y.mean(0).argmax(), (len(F_GRID), len(TH_GRID)))   # 입력을 안 보는 최선 = 라벨 평균 점수 최대 칸
        print(f'고정값 기준선 = 라벨 평균 점수가 가장 높은 칸 ({F_GRID[fa]:.4f} Hz, {np.rad2deg(TH_GRID[fb]):.0f}°)')
        print(f'\n=== T_obs = {tobs:g} s · 학습 샘플 {len(X)}개 (합성 {np.sum(src < 0)}, 실제 변형 {np.sum(src >= 0)}) ===', flush=True)
        models = [train(X[src != r], Y[src != r], args.epochs, seed=r)[:3] for r in range(len(recs))]   # 기록 하나씩 뺀 모델
        for k in args.kscale:
            base = bases[k]; preds = []
            for r, (name, x, y) in enumerate(recs):
                feat, i0 = features(x, y, k, tobs)
                preds.append(predict(*models[r], feat) + (i0,))
            jobs = []
            for r, (name, x, y) in enumerate(recs):
                f, th, i0 = preds[r]
                for mode in args.mode:
                    kw = dict(case='rstlcd', ai_f=f, ai_th=th, k_scale=k)
                    if mode == 'online':
                        kw['t_set'] = i0 * DT + tobs
                    jobs.append(((r, mode), x, y, kw))
            with Pool(args.workers) as pool:
                res = dict(pool.map(sim, jobs))

            print(f'\n--- 건물 강성 × {k:g} (1차 진동수 {R.F0 * np.sqrt(k):.4f} Hz) ---')
            print('기록                              Oracle f, θ      AI f, θ        |  E1b 디튜닝  E2 원문RS  고정값    ' + '  '.join(f'AI {m:6s}' for m in args.mode) + '  E4 Oracle')
            tab = {c: [] for c in ['E1b', 'E2', 'fixed', *args.mode, 'E4']}; ferr = []
            for r, (name, x, y) in enumerate(recs):
                b0 = base[(r, 'E0')]; red = lambda m: score(R.reduction(m, b0))
                grid = {(a, b): red(base[(r, 'E4', a, b)]) for a in range(len(F_GRID)) for b in range(len(TH_GRID))}
                (ga, gb) = max(grid, key=grid.get)
                row = {'E1b': red(base[(r, 'E1b')]), 'E2': red(base[(r, 'E2')]), 'fixed': grid[(fa, fb)], 'E4': grid[(ga, gb)]}
                row.update({m: red(res[(r, m)]) for m in args.mode})
                for c in tab: tab[c].append(row[c])
                f, th, _ = preds[r]; ferr.append(abs(f - F_GRID[ga]))
                print(f'{name[:32]:32s}  {F_GRID[ga]:.4f}, {np.rad2deg(TH_GRID[gb]):3.0f}°  {f:.4f}, {np.rad2deg(th):3.0f}°  |  '
                      + '  '.join(f'{row[c]:9.2f}' for c in tab))
            m = {c: float(np.mean(v)) for c, v in tab.items()}
            gain = {md: (m[md] - m['E2']) / (m['E4'] - m['E2']) * 100 for md in args.mode}
            print('평균                                                             |  ' + '  '.join(f'{m[c]:9.2f}' for c in tab))
            print(f'진동수 예측 오차 평균 {np.mean(ferr) * 1000:.1f} mHz · Oracle 이득 회수율 ' +
                  ', '.join(f'{md} {g:.0f}%' for md, g in gain.items()) +
                  ' · 고정값 대비 ' + ', '.join(f'{md} {m[md] - m["fixed"]:+.2f}%p' for md in args.mode), flush=True)
            summary.append({'tobs': tobs, 'k_scale': k, 'mean': m, 'f_err_mean_hz': float(np.mean(ferr)),
                            'oracle_gain_recovered_pct': gain,
                            'preds': [[recs[r][0], p[0], float(np.rad2deg(p[1]))] for r, p in enumerate(preds)]})

        model, mu, sd, _ = train(X, Y, args.epochs)                 # 전체 데이터로 최종 모델
        torch.save({'state': model.state_dict(), 'mu': mu, 'sd': sd, 'tobs': tobs}, f'models/ai_mlp{TAG}_tobs{tobs:g}.pt')

    out = f'results/ai_eval{TAG}{args.tag}.json' if args.kscale == [1.0] else f'results/ai_eval{TAG}_kscan{args.tag}.json'
    json.dump(summary, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n저장: {out}, models/ai_mlp{TAG}_tobs*.pt')
