# -*- coding: utf-8 -*-
"""[v2: 원문식 모델 · 지진 단위 분리 · 학습 분할 안에서 고른 고정값 · 시드 반복]
진동수 · 회전각 예측 AI 학습과 평가 (`페이퍼/02_AI_학습_계획.md` 4~6절).

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
import rstlcd_cos2 as R
import records
from gen_labels_v2 import DT, F_GRID, TH_GRID, F_RANGE, TAG, OUT as LABEL_DIR

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


def event_of(name):
    """같은 지진(사건)의 다른 관측소 기록은 한 묶음 — 학습에서 같이 뺀다."""
    if name.startswith('PEER') and int(name.split()[1]) in (1, 2, 3, 4, 11):
        return 'ImperialValley1979'
    return name


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--tobs', type=float, nargs='+', default=[5.0])
    ap.add_argument('--mode', nargs='+', default=['preset', 'online'])
    ap.add_argument('--kscale', type=float, nargs='+', default=[1.0])
    ap.add_argument('--epochs', type=int, default=400)
    ap.add_argument('--seeds', type=int, default=5, help='학습 시드 개수 (평균 ± 표준편차 보고)')
    ap.add_argument('--tag', default='')
    ap.add_argument('--workers', type=int, default=max(1, os.cpu_count() - 1))
    args = ap.parse_args()
    print(f'장치: {DEV}' + (f' ({torch.cuda.get_device_name(0)})' if DEV == 'cuda' else ''), flush=True)
    recs = test_records(); n = len(recs); grp = [event_of(nm) for nm, _, _ in recs]
    os.makedirs('results', exist_ok=True); os.makedirs('models', exist_ok=True)
    bases = {k: baselines(recs, k, args.workers) for k in args.kscale}
    shape = (len(F_GRID), len(TH_GRID)); kr = [r for r, (nm, _, _) in enumerate(recs) if ('포항' in nm or '경주' in nm)]
    summary = []
    for tobs in args.tobs:
        X, Y, src = load_labels(tobs)
        masks = [~np.isin(src, [s for s in range(n) if grp[s] == grp[r]]) for r in range(n)]    # 같은 지진의 변형 · 기록 모두 제외
        fixed_cell = [np.unravel_index(Y[masks[r]].mean(0).argmax(), shape) for r in range(n)]   # 학습 분할 안에서 고른 고정값
        print(f'\n=== T_obs = {tobs:g} s · 학습 샘플 {len(X)}개 (합성 {np.sum(src < 0)}, 실제 변형 {np.sum(src >= 0)}) · 시드 {args.seeds}개 ===', flush=True)
        models = {sd: [train(X[masks[r]], Y[masks[r]], args.epochs, seed=100 * sd + r)[:3] for r in range(n)] for sd in range(args.seeds)}
        for k in args.kscale:
            base = bases[k]; preds = {}
            for sd in range(args.seeds):
                for r, (name, x, y) in enumerate(recs):
                    feat, i0 = features(x, y, k, tobs)
                    preds[(sd, r)] = predict(*models[sd][r], feat) + (i0,)
            jobs = []
            for (sd, r), (f, th, i0) in preds.items():
                for mode in args.mode:
                    kw = dict(case='rstlcd', ai_f=f, ai_th=th, k_scale=k)
                    if mode == 'online':
                        kw['t_set'] = i0 * DT + tobs
                    jobs.append(((sd, r, mode), recs[r][1], recs[r][2], kw))
            with Pool(args.workers) as pool:
                res = dict(pool.map(sim, jobs))
            print(f'\n--- 건물 강성 × {k:g} (1차 진동수 {R.F0 * np.sqrt(k):.4f} Hz) ---')
            print('기록                              E1b 디튜닝  E2 원문RS  고정값(학습분할)  ' + '  '.join(f'AI {m:6s}' for m in args.mode) + '  E4 Oracle')
            tab = {c: np.zeros(n) for c in ['E1b', 'E2', 'fixed', 'E4']}; ai = {m: np.zeros((args.seeds, n)) for m in args.mode}; ferr = []
            for r, (name, x, y) in enumerate(recs):
                b0 = base[(r, 'E0')]; red = lambda m: score(R.reduction(m, b0))
                grid = {(a, b): red(base[(r, 'E4', a, b)]) for a in range(shape[0]) for b in range(shape[1])}
                ga, gb = max(grid, key=grid.get)
                tab['E1b'][r], tab['E2'][r], tab['fixed'][r], tab['E4'][r] = red(base[(r, 'E1b')]), red(base[(r, 'E2')]), grid[tuple(fixed_cell[r])], grid[(ga, gb)]
                for m in args.mode:
                    for sd in range(args.seeds): ai[m][sd, r] = red(res[(sd, r, m)])
                ferr += [abs(preds[(sd, r)][0] - F_GRID[ga]) for sd in range(args.seeds)]
                print(f'{name[:32]:32s}  {tab["E1b"][r]:9.2f}  {tab["E2"][r]:9.2f}  {tab["fixed"][r]:12.2f}  '
                      + '  '.join(f'{ai[m][:, r].mean():9.2f}' for m in args.mode) + f'  {tab["E4"][r]:9.2f}')
            mean = {c: float(v.mean()) for c, v in tab.items()}
            out = {'mean': mean, 'f_err_mean_hz': float(np.mean(ferr))}
            print('평균                                                             ' + f'  E1b {mean["E1b"]:.2f}  E2 {mean["E2"]:.2f}  고정 {mean["fixed"]:.2f}  Oracle {mean["E4"]:.2f}')
            for m in args.mode:
                per_seed = ai[m].mean(1); diff = per_seed - mean['fixed']
                rec = (per_seed - mean['E2']) / (mean['E4'] - mean['E2']) * 100
                print(f'AI {m:6s} {per_seed.mean():.2f} ± {per_seed.std():.2f} | 고정값 대비 {diff.mean():+.2f} ± {diff.std():.2f}%p (시드 {args.seeds}개) | Oracle 여지 회수(E2 기준) {rec.mean():.0f}%'
                      + (f' | 한국 기록(포항·경주) AI−고정 {np.mean(ai[m][:, kr].mean(0) - tab["fixed"][kr]):+.2f}%p' if kr else ''))
                out[m] = {'mean': float(per_seed.mean()), 'std': float(per_seed.std()), 'minus_fixed_mean': float(diff.mean()), 'minus_fixed_std': float(diff.std()), 'per_record': ai[m].mean(0).tolist()}
            print(f'진동수 예측 오차 평균 {np.mean(ferr) * 1000:.1f} mHz · Oracle − 고정값 = {mean["E4"] - mean["fixed"]:.2f}%p', flush=True)
            out.update(tobs=tobs, k_scale=k, records=[r_[0] for r_ in recs], per_record=dict((c, v.tolist()) for c, v in tab.items()))
            summary.append(out)
    path = f'results/ai_eval_v2{TAG}{args.tag}.json'
    json.dump(summary, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n저장: {path}')
