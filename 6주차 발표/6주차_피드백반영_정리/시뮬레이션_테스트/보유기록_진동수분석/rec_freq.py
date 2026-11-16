"""보유 지진 기록 7개의 주요 진동수 요약 (예비 분석).
사용: python rec_freq.py <records 폴더>  -> rec_freq.csv, rec_freq.png
- FFT 최대 피크 진동수, 스펙트럼 중심(centroid), 건물 1차 진동수(0.872 Hz) 부근(0.6~1.2 Hz) 에너지 비율
"""
import sys, os, numpy as np, csv
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = ['Malgun Gothic','NanumGothic','Noto Sans CJK KR','AppleGothic','DejaVu Sans']; plt.rcParams['axes.unicode_minus'] = False
D = sys.argv[1] if len(sys.argv) > 1 else '../matlab/w5/records'
FILES = ['elcentro_NS','elcentro_EW','pohang_BUS2_BHN','pohang_BUS2_BHE','gyeongju_BUS2_BHN','gyeongju_CHJ2_BHN','gyeongju_CHJ2_BHE']
F1 = 0.872
rows = []; fig, ax = plt.subplots(len(FILES), 1, figsize=(7, 1.6*len(FILES)), sharex=True)
for a, f in zip(ax, FILES):
    d = np.loadtxt(os.path.join(D, f + '.txt')); t, x = d[:, 0], d[:, 1]
    dt = np.median(np.diff(t)); x = x - x.mean()
    n = 1 << int(np.ceil(np.log2(len(x))) + 1)
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)), n)); fr = np.fft.rfftfreq(n, dt)
    m = (fr > 0.1) & (fr < 20)
    # 1 Hz 이하 잡음 영향을 줄이기 위해 0.1 Hz 이상만 사용
    pk = fr[m][np.argmax(X[m])]
    P = X[m] ** 2; cen = (fr[m] * P).sum() / P.sum()
    band = P[(fr[m] >= 0.6) & (fr[m] <= 1.2)].sum() / P.sum()
    rows.append([f, round(dt, 4), round(t[-1] - t[0], 1), round(float(pk), 2), round(float(cen), 2), round(float(band) * 100, 1)])
    a.plot(fr[m], X[m] / X[m].max(), lw=.8); a.axvline(F1, color='r', lw=.8, ls='--'); a.set_ylabel(f.replace('_', '\n'), fontsize=6); a.set_xlim(0, 10)
ax[-1].set_xlabel('진동수 (Hz)  · 빨간 점선 = 건물 1차 0.872 Hz')
plt.tight_layout(); plt.savefig('rec_freq.png', dpi=130)
with open('rec_freq.csv', 'w', newline='', encoding='utf-8-sig') as fo:
    w = csv.writer(fo); w.writerow(['기록', 'dt(s)', '길이(s)', 'FFT 피크(Hz)', '스펙트럼 중심(Hz)', '0.6~1.2Hz 에너지(%)']); w.writerows(rows)
for r in rows: print(r)
