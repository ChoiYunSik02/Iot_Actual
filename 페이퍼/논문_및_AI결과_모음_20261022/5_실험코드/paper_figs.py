# -*- coding: utf-8 -*-
"""논문 그림 (영문 라벨) — v2 결과(원문식 모델)에서 만든다. 출력: ../그림/*.png
  figG1_spectra        입력 11기록의 푸리에 스펙트럼 + 건물 진동수 + 장치 조정 범위 (교수님 요청: 보유 지진 전체)
  figG2_response       대표 기록: 최상층 변위 시간이력 · 응답 스펙트럼(감쇠된 진동수) · 6지표 저감 (요청: 감쇠 진동수, 상쇄량)
  figG4_values         대표 기록: 장치 진동수 · 개구율 κ · 회전각 시간이력 (요청: 값이 어떻게 바뀌는지)
  figG6_per_record     기록별 저감률 (수동 디튜닝 · 원문 RS · 고정값 · AI preset · Oracle)
  figG7_ai_vs_fixed    AI − 고정값 (사건 단위 평균 ± SE, 9조건)
  figG8_scoremap       칸별 평균 저감률 히트맵 + 각도 의존성
대표 기록: 고정값 − 원문 RS 이득이 평균에 가장 가까운 기록 (최고값만 보여 주지 않기).
사용: python paper_figs.py [--out ../그림] [--tobs 3]
"""
import argparse, glob, json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import rstlcd_cos2 as R
import records
from gen_labels_v2 import F_GRID, TH_GRID, OUT as LABEL_DIR, TAG
from exp_switch import trig_t

DT = 0.01
COL = {'E0': '#8a8985', 'E1b': '#eda100', 'E2': '#2a78d6', 'FX': '#7a4fd1', 'AI': '#eb6834', 'E4': '#1baf7a'}
NAME = {'E0': 'Uncontrolled', 'E1b': 'Detuned passive TLCD', 'E2': 'RS-TLCD (original, wavelet)', 'FX': 'RS-TLCD preset (constant)',
        'AI': 'AI preset', 'E4': 'Oracle (constant)'}
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#e3e2de'
plt.rcParams.update({'font.family': ['Arial', 'DejaVu Sans'], 'axes.unicode_minus': False, 'font.size': 9, 'axes.edgecolor': MUTED,
                     'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.grid': True, 'grid.color': GRID,
                     'grid.linewidth': 0.6, 'axes.spines.top': False, 'axes.spines.right': False, 'lines.linewidth': 1.3,
                     'legend.frameon': False, 'savefig.dpi': 200, 'savefig.bbox': 'tight'})
IV = [0, 1, 2, 3, 4]


def short(nm):
    nm = nm.replace('포항 2017 BUS2', 'Pohang 2017').replace('경주 2016 CHJ2', 'Gyeongju 2016')
    return (nm.replace('PEER ', '#').replace('El Centro Differential Array', 'El Centro Diff.').replace('Aeropuerto Mexicali', 'Mexicali')
            .replace('El Centro Array ', 'El Centro ').replace(' 2017 BUS2', ' 2017').replace(' 2016 CHJ2', ' 2016'))[:22]


def events(n):
    return [IV] + [[i] for i in range(5, n)]


def load_eval(path):
    return json.load(open(path, encoding='utf-8'))


def fixed_cell_excluding(excl_src):
    """학습 라벨 평균 점수가 최대인 칸 (시험 기록 · 같은 지진의 변형 제외)."""
    S = []
    for p in sorted(glob.glob(os.path.join(LABEL_DIR, 's*.npz'))):
        d = np.load(p); m = json.loads(str(d['meta']))
        if m['kind'] == 'real' and m['src'] in excl_src: continue
        s = d['score']; S.append(s - s.mean())
    return np.unravel_index(np.mean(S, 0).argmax(), S[0].shape), len(S)


def sim(x, y, kind, cell=None):
    if kind == 'E0': return R.simulate(x, y, DT, case='none')
    if kind == 'E2': return R.simulate(x, y, DT, case='rstlcd', c_scale=30.0)
    a, b = cell; f, th = float(F_GRID[a]), float(TH_GRID[b])
    return R.simulate(x, y, DT, case='rstlcd', c_scale=30.0, f0=f, theta0=th, rs_freq=lambda t, s: f, rs_theta=lambda t, s: th)


def fig_g1(recs, out):
    fig, axs = plt.subplots(3, 4, figsize=(10, 6.2), sharex=True, sharey=True); axs = axs.ravel()
    for i, (nm, x, y) in enumerate(recs):
        ax = axs[i]; f = np.fft.rfftfreq(len(x), DT)
        for v, c, lab in ((x, '#2a78d6', 'X'), (y, '#eb6834', 'Y')):
            A = np.abs(np.fft.rfft(v)) * DT; k = 9; A = np.convolve(A, np.ones(k) / k, 'same')
            ax.loglog(f[1:], A[1:] + 1e-9, color=c, lw=0.9, label=lab)
        ax.axvspan(0.3204, 0.3542, color='#1baf7a', alpha=0.35, lw=0); ax.axvline(1.0112, color=MUTED, lw=0.8, ls=':')
        ax.set_title(short(nm), fontsize=8.5, loc='left'); ax.set_xlim(0.05, 20); ax.set_ylim(1e-4, 1)
    axs[0].legend(fontsize=7, loc='lower left'); axs[-1].axis('off')
    axs[-1].text(0.0, 0.7, 'green band: tunable range 0.3204–0.3542 Hz\ndotted line: 2nd mode 1.011 Hz', fontsize=8, color=MUTED, transform=axs[-1].transAxes)
    for ax in axs[8:11]: ax.set_xlabel('Frequency (Hz)')
    for ax in axs[::4]: ax.set_ylabel('Fourier amplitude')
    fig.suptitle('Input ground motions (scaled to 35 cm/s² per component)', x=0.01, ha='left', fontsize=10)
    fig.savefig(os.path.join(out, 'figG1_spectra.png')); plt.close(fig)


def fig_g2_g4(recs, ev, out, tobs):
    e = ev[0]; n = len(recs); k1 = next(x for x in ev if abs(x['k_scale'] - 1.0) < 1e-9 and x['tobs'] == tobs)
    gain = np.array(k1['per_record']['fixed']) - np.array(k1['per_record']['E2'])
    r = int(np.argmin(np.abs(gain - gain.mean()))); nm, x, y = recs[r]
    (a, b), nlab = fixed_cell_excluding({s for s in range(n) if (s in IV) == (r in IV) and (r in IV or s == r)})
    print(f'대표 기록 {nm} (고정 − E2 = {gain[r]:+.2f}, 평균 {gain.mean():+.2f}); 고정칸 f={F_GRID[a]:.4f} Hz θ={np.rad2deg(TH_GRID[b]):.0f}° (라벨 {nlab}개)')
    o = {'E0': sim(x, y, 'E0'), 'E2': sim(x, y, 'E2'), 'FX': sim(x, y, 'FX', (a, b))}
    t = o['E0']['t'] if 't' in o['E0'] else np.arange(len(x)) * DT; t0 = trig_t(x, y)
    fig = plt.figure(figsize=(10, 6.4)); gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], hspace=0.38, wspace=0.28)
    ax = fig.add_subplot(gs[0, :])
    for kk in ('E0', 'E2', 'FX'): ax.plot(t, 100 * o[kk]['ux'], color=COL[kk], lw=1.0 if kk == 'E0' else 1.2, label=NAME[kk])
    ax.axvline(t0, color=MUTED, lw=0.8, ls=(0, (2, 2))); ax.set_xlim(0, 45); ax.set_xlabel('Time (s)'); ax.set_ylabel('Roof X displacement (cm)')
    ax.set_title(f'(a) {short(nm)}: roof displacement', loc='left', fontsize=9); ax.legend(ncol=3, fontsize=8, loc='upper right')
    ax = fig.add_subplot(gs[1, 0]); f = np.fft.rfftfreq(len(t), DT)
    for kk in ('E0', 'E2', 'FX'): ax.plot(f, np.abs(np.fft.rfft(o[kk]['ux'])) * DT * 100, color=COL[kk], label=NAME[kk])
    ax.axvspan(0.3204, 0.3542, color='#1baf7a', alpha=0.25, lw=0); ax.set_xlim(0.1, 1.3); ax.set_xlabel('Frequency (Hz)'); ax.set_ylabel('Roof X amplitude (cm·s)')
    ax.set_title('(b) response spectrum', loc='left', fontsize=9)
    ax = fig.add_subplot(gs[1, 1]); keys = ['ux_max', 'uy_max', 'th_max', 'ux_rms', 'uy_rms', 'th_rms']
    lab = ['X peak', 'Y peak', 'θ peak', 'X RMS', 'Y RMS', 'θ RMS']; b0 = R.metrics(o['E0']); w = 0.38; xx = np.arange(6)
    for j, kk in enumerate(('E2', 'FX')):
        red = R.reduction(R.metrics(o[kk]), b0); ax.bar(xx + (j - 0.5) * w, [red[q] for q in keys], w, color=COL[kk], label=NAME[kk])
    ax.set_xticks(xx); ax.set_xticklabels(lab, fontsize=8); ax.set_ylabel('Reduction (%)'); ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_title('(c) reduction of the six indices', loc='left', fontsize=9); ax.set_ylim(top=ax.get_ylim()[1] * 1.45); ax.legend(fontsize=7.5, loc='upper right')
    fig.savefig(os.path.join(out, 'figG2_response.png')); plt.close(fig)
    fig, axs = plt.subplots(3, 1, figsize=(8, 6), sharex=True)
    for kk in ('E2', 'FX'):
        axs[0].plot(t, o[kk]['f_dev'], color=COL[kk], label=NAME[kk]); axs[1].plot(t, o[kk]['kappa'], color=COL[kk], lw=0.8)
        axs[2].plot(t, np.rad2deg(o[kk]['theta']), color=COL[kk])
    for q in axs: q.axvline(t0, color=MUTED, lw=0.8, ls=(0, (2, 2)))
    axs[0].set_ylabel('Damper frequency (Hz)'); axs[1].set_ylabel('Orifice opening κ'); axs[2].set_ylabel('Rotation angle (°)'); axs[2].set_xlabel('Time (s)')
    axs[0].set_ylim(0.31, 0.362); axs[0].legend(fontsize=8, loc='lower left'); axs[2].set_xlim(0, 45); axs[0].set_title(f'{short(nm)}: how the three actuators move', loc='left', fontsize=9)
    fig.savefig(os.path.join(out, 'figG4_values.png')); plt.close(fig)
    return nm


def fig_g6(ev, out, tobs):
    k1 = next(x for x in ev if abs(x['k_scale'] - 1.0) < 1e-9 and x['tobs'] == tobs); names = k1['records']; n = len(names)
    series = [('E1b', k1['per_record']['E1b']), ('E2', k1['per_record']['E2']), ('FX', k1['per_record']['fixed']),
              ('AI', k1['preset']['per_record']), ('E4', k1['per_record']['E4'])]
    fig, ax = plt.subplots(figsize=(11, 3.8)); w = 0.16; xx = np.arange(n)
    for j, (kk, v) in enumerate(series): ax.bar(xx + (j - 2) * w, v, w, color=COL[kk], label=NAME[kk])
    ax.set_xticks(xx); ax.set_xticklabels([short(s) for s in names], rotation=25, ha='right', fontsize=8); ax.set_ylabel('Mean reduction of six indices (%)')
    ax.axhline(0, color=MUTED, lw=0.8); ax.legend(ncol=5, fontsize=7.5, loc='lower center', bbox_to_anchor=(0.5, 1.0), handlelength=1.2, columnspacing=1.0)
    ax.set_title(f'Nominal building, T_obs = {tobs:g} s (AI: mean of five seeds)', loc='left', fontsize=9, pad=26)
    fig.savefig(os.path.join(out, 'figG6_per_record.png')); plt.close(fig)


def fig_g7(ev, out):
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.3), sharey=True)
    for ax, k in zip(axs, sorted({e['k_scale'] for e in ev})):
        for j, (mode, c) in enumerate((('preset', COL['AI']), ('online', '#8a5a2b'))):
            xs, ms, ses = [], [], []
            for e in sorted([q for q in ev if q['k_scale'] == k], key=lambda q: q['tobs']):
                d = np.array(e[mode]['per_record']) - np.array(e['per_record']['fixed']); de = np.array([d[g].mean() for g in events(len(d))])
                xs.append(e['tobs'] + (j - 0.5) * 0.18); ms.append(de.mean()); ses.append(de.std(ddof=1) / np.sqrt(len(de)))
            ax.errorbar(xs, ms, yerr=ses, fmt='o' if mode == 'preset' else 's', color=c, capsize=3, label=f'AI {mode}', ms=4.5)
        ax.axhline(0, color=MUTED, lw=0.9); ax.set_xticks([1, 3, 5]); ax.set_xlabel('Observation time T_obs (s)')
        ax.set_title(f'Building {R.F0 * np.sqrt(k):.4f} Hz', loc='left', fontsize=9)
    axs[0].set_ylabel('AI − constant setting (points)'); axs[0].legend(fontsize=8)
    fig.suptitle('Difference to the constant pre-set damper, mean ± s.e. over seven earthquakes', x=0.01, ha='left', fontsize=9.5, y=1.03)
    fig.savefig(os.path.join(out, 'figG7_ai_vs_fixed.png')); plt.close(fig)


def fig_g8(out, base_path):
    d = {tuple(json.loads(k)): v for k, v in json.load(open(base_path, encoding='utf-8')).items()}
    n = max(k[0] for k in d) + 1; nF, nT = len(F_GRID), len(TH_GRID); S = np.zeros((n, nF, nT))
    for r in range(n):
        b0 = d[(r, 'E0')]
        for a in range(nF):
            for b in range(nT): S[r, a, b] = np.mean(list(R.reduction(d[(r, 'E4', a, b)], b0).values()))
    m = S.mean(0); fa, fb = np.unravel_index(m.argmax(), m.shape); orc = S.reshape(n, -1).max(1).mean()
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={'width_ratios': [1.05, 1], 'wspace': 0.5})
    im = axs[0].imshow(m, origin='lower', aspect='auto', cmap='viridis'); axs[0].grid(False)
    axs[0].set_xticks(range(nT)); axs[0].set_xticklabels([f'{np.rad2deg(t):.0f}' for t in TH_GRID]); axs[0].set_yticks(range(nF)); axs[0].set_yticklabels([f'{f:.3f}' for f in F_GRID])
    axs[0].set_xlabel('Rotation angle θ (°)'); axs[0].set_ylabel('Damper frequency (Hz)'); axs[0].plot(fb, fa, 'w*', ms=11)
    axs[0].set_title('(a) mean reduction (%), eleven records', loc='left', fontsize=9); fig.colorbar(im, ax=axs[0], fraction=0.046)
    for a, c in ((fa, COL['FX']), (0, COL['E1b'])):
        axs[1].plot(np.rad2deg(TH_GRID), m[a], 'o-', color=c, ms=4, label=f'f = {F_GRID[a]:.4f} Hz')
    axs[1].axhline(orc, color=COL['E4'], ls='--', label=f'Oracle mean {orc:.2f}'); axs[1].set_xlabel('Rotation angle θ (°)'); axs[1].set_ylabel('Mean reduction (%)')
    axs[1].set_title('(b) angle dependence (★ = best constant)', loc='left', fontsize=9); axs[1].legend(fontsize=8)
    fig.savefig(os.path.join(out, 'figG8_scoremap.png')); plt.close(fig)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join('..', '그림')); ap.add_argument('--tobs', type=float, default=3.0)
    args = ap.parse_args(); os.makedirs(args.out, exist_ok=True)
    recs = [(f'PEER {no} {st}', x, y) for no, st, x, y in records.paper_pairs(DT)[0]] + records.held_pairs(DT)
    ev = load_eval(f'results/ai_eval_v2{TAG}.json')
    fig_g1(recs, args.out); print('G1 ok'); nm = fig_g2_g4(recs, ev, args.out, args.tobs); print('G2, G4 ok')
    fig_g6(ev, args.out, args.tobs); print('G6 ok'); fig_g7(ev, args.out); print('G7 ok')
    fig_g8(args.out, f'results/ai_eval_baselines{TAG}.json'); print('G8 ok →', os.path.abspath(args.out))
