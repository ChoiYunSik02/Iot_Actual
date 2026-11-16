# -*- coding: utf-8 -*-
"""AI 학습용 라벨 생성 (`페이퍼/02_AI_학습_계획.md` 2·3절).

샘플 하나 = (지진 X·Y 가속도, 건물 강성 배율 k) → Oracle 49칸 점수 지도 (진동수 7 × 회전각 7, 6개 지표 평균 저감률 %)
  - 합성 지진: Kanai-Tajimi + Clough-Penzien 필터 백색잡음 × Jennings 포락선
  - 실제 기록 변형: PEER 8쌍 + 보유 3쌍을 회전 · 시간 늘이기 (src = 원본 번호, 시험할 때 같은 원본 변형은 학습에서 뺌)
결과: data/labels/s00000.npz … (중간에 끊겨도 다시 실행하면 이어서 함)
진행 상황: data/labels/progress.html 을 브라우저로 열면 10초마다 새로 고침됨
사용: python gen_labels.py [--n 2000] [--real-frac 0.25] [--workers 15]
     범위 확대: TLCD_FRANGE=0.2 TLCD_NF=13 python gen_labels.py  (→ data/labels_r20/)
"""
import argparse, glob, html, json, os, time
from multiprocessing import Pool
import numpy as np
import rstlcd as R
import records

DT = 0.01
# 장치 진동수 조절 범위: 환경변수로 바꿈 (작업 프로세스 · train_ai.py까지 같은 값이 전달되도록). 기본 = 원문 ±5%
FR = float(os.environ.get('TLCD_FRANGE', '0.05'))
NF, NTH = int(os.environ.get('TLCD_NF', '7')), 7
F_RANGE = R.F_RANGE if FR == 0.05 else (R.F0 * (1 - FR), R.F0 * (1 + FR))
TAG = '' if FR == 0.05 else f'_r{FR * 100:g}'                    # 결과 파일 이름 꼬리표
SRC = os.environ.get('TLCD_SOURCE', 'kt')                        # kt = 기존 합성 + 실제 변형, mr = 규모·거리·지반 확률론적 지진동 (조기경보 실험)
TAG += '' if SRC == 'kt' else '_' + SRC
F_GRID = np.linspace(*F_RANGE, NF)
TH_GRID = np.deg2rad(np.linspace(0, 90, NTH))
K_RANGE = (0.81, 1.21)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'labels' + TAG)


# ── 합성 지진 ─────────────────────────────────────────────────
def kt_filter(n, fg, zg, rng):
    """백색잡음 → Kanai-Tajimi(fg, zg) × Clough-Penzien 고역 통과 (주파수 영역)."""
    w = 2 * np.pi * np.fft.rfftfreq(n, DT)
    wg, wf = 2 * np.pi * fg, 2 * np.pi * fg / 10
    kt = (wg ** 4 + 4 * zg ** 2 * wg ** 2 * w ** 2) / ((wg ** 2 - w ** 2) ** 2 + 4 * zg ** 2 * wg ** 2 * w ** 2)
    cp = w ** 4 / ((wf ** 2 - w ** 2) ** 2 + 4 * 0.6 ** 2 * wf ** 2 * w ** 2)
    return np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * np.sqrt(kt * cp), n)


def synthetic(rng):
    dur = rng.uniform(15, 40); n = int(dur / DT); t = np.arange(n) * DT
    t1, t2 = rng.uniform(1, 4), dur * rng.uniform(0.3, 0.6)
    env = np.where(t < t1, (t / t1) ** 2, np.where(t < t2, 1.0, np.exp(-rng.uniform(0.15, 0.5) * (t - t2))))
    fg = np.exp(rng.uniform(np.log(0.5), np.log(8.0))); zg = rng.uniform(0.2, 0.6)
    a = kt_filter(n, fg, zg, rng)
    b = kt_filter(n, fg * rng.uniform(0.8, 1.25), zg, rng)
    rho = rng.uniform(0, 0.6)                                       # X-Y 상관
    x, y = a, rho * a + np.sqrt(1 - rho ** 2) * b
    y *= rng.uniform(0.5, 1.0)                                      # 세기 비
    if rng.random() < 0.5: x, y = y, x
    return x * env, y * env, dict(kind='synthetic', fg=float(fg), zg=float(zg), dur=float(dur))


SITE_FG = (8.0, 3.0, 1.2)                                         # 지반 등급 0 암반 · 1 단단한 흙 · 2 연약 지반의 탁월 진동수 [Hz]


def synthetic_mr(rng):
    """Boore (2003) 확률론적 방법: Brune ω² 원천 × 기하 감쇠 × Q × κ0 × 지반 필터(Kanai-Tajimi), Saragoni-Hart 포락선.
    조기경보가 주는 정보 = 규모 M, 진원 거리 R, 지반 등급. 응력 강하 · 잡음은 경보가 모르는 무작위 성분."""
    M = rng.uniform(5.0, 8.0); Rk = np.exp(rng.uniform(np.log(10), np.log(300))); site = int(rng.integers(3))
    beta, dsig = 3.5, np.exp(rng.uniform(np.log(30), np.log(300)))                     # km/s, bar
    M0 = 10 ** (1.5 * M + 16.05); fc = 4.906e6 * beta * (dsig / M0) ** (1 / 3)
    dur = 1 / fc + 0.05 * Rk; T = dur * 1.3 + 5; n = int(T / DT); t = np.arange(n) * DT
    f = np.fft.rfftfreq(n, DT); f[0] = 1e-6
    G = np.where(Rk < 70, 1 / Rk, np.where(Rk < 130, 1 / 70, 1 / 70 * (130 / Rk) ** 0.5))
    fas = (2 * np.pi * f) ** 2 / (1 + (f / fc) ** 2) * G * np.exp(-np.pi * f * Rk / (180 * f ** 0.45 * beta)) * np.exp(-np.pi * 0.04 * f)
    wg, zg = 2 * np.pi * SITE_FG[site], rng.uniform(0.3, 0.5); w = 2 * np.pi * f
    fas *= np.sqrt((wg ** 4 + 4 * zg ** 2 * wg ** 2 * w ** 2) / ((wg ** 2 - w ** 2) ** 2 + 4 * zg ** 2 * wg ** 2 * w ** 2))
    eps, eta, tn = 0.2, 0.05, 2.0 * dur                                                   # Saragoni-Hart
    bb = -eps * np.log(eta) / (1 + eps * (np.log(eps) - 1)); cc = bb / eps; aa = (np.e / eps) ** bb
    tt = np.clip(t / tn, 1e-9, None); env = aa * tt ** bb * np.exp(-cc * tt) * (t < tn)
    def one():
        A = np.fft.rfft(rng.standard_normal(n) * env); A /= np.sqrt(np.mean(np.abs(A) ** 2))
        return np.fft.irfft(A * fas, n)
    x, y = one(), one() * rng.uniform(0.5, 1.0)
    return x, y, dict(kind='mr', M=float(M), R=float(Rk), site=site, dsig=float(dsig), dur=float(T))


def real_variant(rng, pool):
    src = int(rng.integers(len(pool))); name, x, y = pool[src]
    phi = rng.uniform(0, np.pi); c, s = np.cos(phi), np.sin(phi)
    x, y = c * x + s * y, -s * x + c * y                            # 수평면 회전
    st = rng.uniform(0.7, 1.4)                                      # 시간 늘이기 → 탁월 진동수 1/st배
    t = np.arange(len(x)) * DT; tn = np.arange(0, t[-1] * st, DT)
    x, y = np.interp(tn / st, t, x), np.interp(tn / st, t, y)
    return x, y, dict(kind='real', src=src, src_name=name, rot_deg=float(np.rad2deg(phi)), stretch=float(st))


def make_sample(i, real_frac, pool):
    rng = np.random.default_rng(1000 + i)
    if SRC == 'mr':
        x, y, meta = synthetic_mr(rng)
    else:
        x, y, meta = real_variant(rng, pool) if rng.random() < real_frac else synthetic(rng)
    x, y = (np.r_[v, np.zeros(int(10 / DT))] for v in (x, y))      # 자유진동 10 s
    x, y = x / np.abs(x).max() * records.PGA_TARGET, y / np.abs(y).max() * records.PGA_TARGET
    meta['k_scale'] = float(rng.uniform(*K_RANGE))
    return x, y, meta


# ── 라벨 ─────────────────────────────────────────────────────
def label(job):
    i, real_frac, pool, c_scale = job
    path = os.path.join(OUT, f's{i:05d}.npz')
    if os.path.exists(path):
        return i, None
    t0 = time.time()
    x, y, meta = make_sample(i, real_frac, pool)
    kw = dict(c_scale=c_scale, k_scale=meta['k_scale'], f_range=F_RANGE)
    base = R.metrics(R.simulate(x, y, DT, 'none', **kw))
    score = np.zeros((NF, NTH))
    for a, f in enumerate(F_GRID):
        for b, th in enumerate(TH_GRID):
            o = R.simulate(x, y, DT, 'rstlcd', f0=f, theta0=th, rs_freq=lambda t, s: f, rs_theta=lambda t, s: th, **kw)
            score[a, b] = np.mean(list(R.reduction(R.metrics(o), base).values()))
    a, b = np.unravel_index(np.argmax(score), score.shape)
    meta.update(f_star=float(F_GRID[a]), theta_star_deg=float(np.rad2deg(TH_GRID[b])), best=float(score[a, b]),
                sec=time.time() - t0)
    np.savez_compressed(path, agx=x.astype(np.float32), agy=y.astype(np.float32), score=score,
                        f_grid=F_GRID, th_grid_deg=np.rad2deg(TH_GRID), meta=json.dumps(meta, ensure_ascii=False))
    return i, meta


# ── 진행 상황 페이지 ───────────────────────────────────────────
def load_metas():
    metas = []
    for p in sorted(glob.glob(os.path.join(OUT, 's*.npz'))):
        try:
            metas.append(json.loads(str(np.load(p)['meta'])))
        except Exception:
            pass
    return metas


def desc(m):
    if m['kind'] == 'mr':
        return f"M{m['M']:.1f} · {m['R']:.0f} km · 지반 {m['site']}"
    return m['kind'] + (' · ' + m['src_name'] if m['kind'] == 'real' else f" · fg {m['fg']:.2f} Hz")


def write_progress(n, metas, t_start, n_start, recent, finished=False):
    k = len(metas); el = time.time() - t_start; rate = (k - n_start) / el if el > 0 and k > n_start else 0
    eta = (n - k) / rate if rate else float('nan')
    fmt = lambda s: '—' if s != s else f'{int(s // 3600)}시간 {int(s % 3600 // 60)}분'

    def hist(vals, bins, labels):
        cnt = [sum(1 for v in vals if abs(v - b) < 1e-6) for b in bins]; mx = max(cnt + [1])
        return ''.join(f'<tr><td>{l}</td><td><div class="bar" style="width:{200 * c / mx:.0f}px"></div></td><td>{c}</td></tr>'
                       for l, c in zip(labels, cnt))
    fs = [m['f_star'] for m in metas]; ths = [m['theta_star_deg'] for m in metas]
    rows = ''.join(f'<tr><td>{i}</td><td>{html.escape(desc(m))}</td>'
                   f'<td>{m["k_scale"]:.3f}</td><td>{m["f_star"]:.4f}</td><td>{m["theta_star_deg"]:.0f}</td><td>{m["best"]:.1f}</td><td>{m["sec"]:.0f}</td></tr>'
                   for i, m in recent[-12:][::-1])
    pct = 100 * k / n
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">{'' if finished else '<meta http-equiv="refresh" content="10">'}
<title>AI 라벨 생성 진행</title><style>
:root{{--bg:#fff;--fg:#1a1a1a;--mut:#666;--acc:#2f6fdf;--line:#e3e3e3}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16181c;--fg:#e8e8e8;--mut:#9aa;--acc:#6ea0ff;--line:#333}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;max-width:860px;margin:24px auto;padding:0 16px}}
.prog{{height:22px;background:var(--line);border-radius:6px;overflow:hidden}}.prog div{{height:100%;background:var(--acc)}}
.bar{{height:12px;background:var(--acc);border-radius:3px}}table{{border-collapse:collapse;width:100%;margin:8px 0 20px}}
td,th{{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left;font-variant-numeric:tabular-nums}}.mut{{color:var(--mut)}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}@media (max-width:600px){{.grid{{grid-template-columns:1fr}}}}</style></head><body>
<h1>AI 학습 라벨 생성 {'— 완료' if finished else ''}</h1>
<p><b>{k} / {n}</b> 샘플 ({pct:.1f}%) · 속도 {rate * 3600:.0f}개/시간 · 남은 시간 약 {fmt(eta)} · 경과 {fmt(el)}</p>
<div class="prog"><div style="width:{pct:.1f}%"></div></div>
<p class="mut">갱신 {time.strftime('%H:%M:%S')} · 이 페이지는 10초마다 새로 고침 · 중간에 멈춰도 다시 실행하면 이어서 함</p>
<div class="grid"><div><h3>정답 진동수 f* 분포</h3><table>{hist(fs, F_GRID, [f'{f:.4f} Hz' for f in F_GRID])}</table></div>
<div><h3>정답 회전각 θ* 분포</h3><table>{hist(ths, np.rad2deg(TH_GRID), [f'{t:.0f}°' for t in np.rad2deg(TH_GRID)])}</table></div></div>
<h3>최근 샘플</h3><table><tr><th>번호</th><th>종류</th><th>건물 강성 배율</th><th>f* [Hz]</th><th>θ* [°]</th><th>최대 저감 [%]</th><th>계산 [s]</th></tr>{rows}</table>
</body></html>"""
    tmp = os.path.join(OUT, 'progress.tmp')
    open(tmp, 'w', encoding='utf-8').write(page); os.replace(tmp, os.path.join(OUT, 'progress.html'))
    return k


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=2000)
    ap.add_argument('--real-frac', type=float, default=0.25)
    ap.add_argument('--workers', type=int, default=max(1, os.cpu_count() - 1))
    ap.add_argument('--cscale', type=float, default=30.0)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    pool_rec = [(f'PEER {no} {st}', x, y) for no, st, x, y in records.paper_pairs(DT)[0]] + records.held_pairs(DT)
    t_start = time.time(); recent = []
    metas = load_metas()
    n_start = write_progress(args.n, metas, t_start, len(metas), recent)
    print(f'시작: {n_start}/{args.n} 이미 있음 · 진행 상황: {os.path.join(OUT, "progress.html")}', flush=True)
    jobs = [(i, args.real_frac, pool_rec, args.cscale) for i in range(args.n)]
    with Pool(args.workers) as pool:
        for i, meta in pool.imap_unordered(label, jobs):
            if meta:
                recent.append((i, meta)); metas.append(meta)
                k = write_progress(args.n, metas, t_start, n_start, recent)
                print(f'{k}/{args.n}  s{i:05d}  {meta["kind"]:9s} k={meta["k_scale"]:.3f}  f*={meta["f_star"]:.4f}  '
                      f'θ*={meta["theta_star_deg"]:.0f}°  {meta["best"]:.1f}%  ({meta["sec"]:.0f}s)', flush=True)
    write_progress(args.n, metas, t_start, n_start, recent, finished=True)
    print('완료', flush=True)
