"""test2 (9주차 계획 8절 + 8절 추가). 두 단계로 쓴다.

  python run_test2.py add <NGA 다운로드 폴더> [...]   # 선택 규칙대로 기록을 골라 페이퍼/입력/PEER/TEST2로 복사, manifest에 split=test2 추가
  (기록 목록을 커밋한 뒤)
  python run_test2.py run                              # 한 번만 실행

선택 규칙 (8절): 사건마다 Rrup <= 60 km, 180 <= Vs30 <= 760 m/s 중 Rrup가 가장 작은 3개까지. 이미 쓴 사건·여진은 제외.
"""
import os, sys, csv, glob, shutil, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled, Tracked, Peak, Fix45, boot_ci, PEER
from peak_v2 import PeakV2
from sens import Noisy

MAN = os.path.join(PEER, 'record_manifest.csv')
DST = os.path.join(PEER, 'TEST2')
# 이미 쓴 사건 (원문·dev, test, 8주차 학습). 이름 앞부분으로 비교한다 (여진 'Chi-Chi_ Taiwan-03' 등도 걸림)
USED = ['Imperial Valley', 'Northridge', 'Kobe', 'Chi-Chi', 'Cape Mendocino', 'Denali', 'Erzican', 'Erzincan', 'Friuli',
        'Gazli', 'Hector Mine', 'Irpinia', 'Kocaeli', 'Landers', 'Loma Prieta', 'Nahanni', 'Superstition Hills',
        'San Fernando', 'Duzce', 'Manjil', 'Chuetsu', 'San Simeon', 'Pohang', 'Gyeongju']
# 후보 본진 (8절). 이름이 정확히 이것이어야 한다 (여진 제외)
MAIN = ['Chalfant Valley-02', 'Coalinga-01', 'Morgan Hill', 'Whittier Narrows-01', 'N. Palm Springs', 'Big Bear-01',
        'Parkfield-02_ CA', 'Tabas_ Iran', 'Iwate_ Japan', 'Darfield_ New Zealand', 'Christchurch_ New Zealand',
        "L'Aquila_ Italy", 'El Mayor-Cucapah_ Mexico', 'Wenchuan_ China']


def add(folders):
    old = list(csv.DictReader(open(MAN, encoding='utf-8-sig')))
    have = {r['rsn'] for r in old}; cand = {}
    for fo in folders:
        for p in glob.glob(os.path.join(fo, '_SearchResults*.csv')):
            for line in open(p, encoding='utf-8', errors='replace'):
                if ', SRSS,' not in line: continue
                c = next(csv.reader([line], skipinitialspace=True))
                rsn, tp, ev, yr, st, mag, mech, rjb, rrup, vs30 = c[2], c[5], c[9], c[10], c[11], c[12], c[13], c[14], c[15], c[16]
                h1, h2 = c[-3].strip(), c[-2].strip()
                if ev not in MAIN or any(ev.startswith(u) for u in USED) or rsn in have: continue
                if not (float(rrup) <= 60 and 180 <= float(vs30) <= 760): continue
                if any(w in st.lower() for w in ('bldg', 'basement')): continue  # 건물 안 기록 제외 (8절 보충)
                if not (os.path.exists(os.path.join(fo, h1)) and os.path.exists(os.path.join(fo, h2))): continue
                cand.setdefault(ev, {})[rsn] = dict(rsn=rsn, set='TEST2', event=ev.replace('_', ','), year=yr, station=st,
                                                    mag=mag, mechanism=mech, rjb_km=rjb, rrup_km=rrup, vs30=vs30,
                                                    pulse_tp_s=tp if tp != '-' else '', h1=h1, h2=h2, split='test2', _src=fo)
    os.makedirs(DST, exist_ok=True); new = []
    for ev, d in sorted(cand.items()):
        for r in sorted(d.values(), key=lambda r: float(r['rrup_km']))[:3]:
            for h in ('h1', 'h2'): shutil.copy(os.path.join(r['_src'], r[h]), DST)
            r.pop('_src'); new.append(r)
    with open(MAN, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(old[0])); w.writeheader(); w.writerows(old + new)
    print(f'test2: {len(new)}쌍, {len({r["event"] for r in new})}사건')
    for r in new: print(' ', r['event'], r['rsn'], r['station'], r['rrup_km'], r['vs30'])
    print('빠진 후보 사건:', [e for e in MAIN if e not in cand])


POL = {'R': lambda dt: Tracked(dt), 'FIX45': lambda dt: Fix45(dt), 'PEAK': lambda dt: Peak(dt),
       'LP': lambda dt: PeakV2(dt, gap=0.0), 'PEAK_V': lambda dt: _v(Peak(dt)), 'LP_V': lambda dt: _v(PeakV2(dt, gap=0.0))}
NOISY = ['R', 'PEAK', 'LP', 'LP_V']
_plants = {}


def _v(P):
    P.nc = 1; return P


def job(a):
    pol, rec, j, p, seed, urms = a
    ax, ay, dt = load(rec)
    if pol == 'U': return a[:5], uncontrolled(ax, ay, dt).tolist()
    if dt not in _plants: _plants[dt] = Plant(dt)
    if len(_plants[dt].cache) > 200: _plants[dt].cache.clear()
    P = POL[pol](dt); ctrl = P
    if p > 0:
        g = np.random.default_rng([seed, j, 8600])
        ctrl = Noisy(P, g.normal(0, p * urms[0], len(ax)), g.normal(0, p * urms[1], len(ax)))
    y, _, _ = simulate(_plants[dt], ax, ay, ctrl)
    return a[:5], metrics(y).tolist()


def effect(recs, red, a, b):
    ev = lambda r: r[1].replace(',', '').split()[0]; evs = sorted({ev(r) for r in recs})
    d = red[a].mean(1) - red[b].mean(1)
    de = np.array([d[[j for j, r in enumerate(recs) if ev(r) == e]].mean() for e in evs])
    return dict(dS_evt=float(de.mean()), ci95=boot_ci(de), n_evt_better=int((de > 0).sum()), n_evt=len(evs),
                n_rec_better=int((d > 0).sum()), n_rec=len(recs),
                thmax_worse=int((red[a][:, 4] < red[b][:, 4] - 1e-9).sum()), thmax_mean=float((red[a][:, 4] - red[b][:, 4]).mean()),
                per_metric=(red[a] - red[b]).mean(0).round(2).tolist(), per_event=dict(zip(evs, de.round(2).tolist())))


def run():
    t0 = time.time(); recs = rs.record_list('test2'); assert recs, 'test2 기록 없음 (add 먼저)'
    with ProcessPoolExecutor(max_workers=12) as ex:
        U = {a[2]: np.array(m) for a, m in ex.map(job, [('U', r, j, 0, 0, None) for j, r in enumerate(recs)])}
        U = [U[j] for j in range(len(recs))]; urms = [(u[1] / 100, u[3] / 100) for u in U]
        jobs = [(p, r, j, 0.0, 0, None) for p in POL for j, r in enumerate(recs)]
        jobs += [(p, r, j, 0.05, s, urms[j]) for p in NOISY for s in range(5) for j, r in enumerate(recs)]
        res = {}
        for a, m in ex.map(job, jobs, chunksize=2):
            res[(a[0], a[2], a[3], a[4])] = np.array(m)
            if len(res) % 100 == 0: print(f'{len(res)}/{len(jobs)} {time.time() - t0:.0f}s', flush=True)
    red = lambda p, n, s: np.array([(1 - res[(p, j, n, s)] / U[j]) * 100 for j in range(len(recs))])
    R0 = {p: red(p, 0.0, 0) for p in POL}
    out = dict(n_records=len(recs), events=sorted({r[1] for r in recs}), score={p: float(v.mean()) for p, v in R0.items()})
    out['main'] = {'PEAK-R': effect(recs, R0, 'PEAK', 'R'), 'PEAK-FIX45': effect(recs, R0, 'PEAK', 'FIX45'),
                   'LP_V-R': effect(recs, R0, 'LP_V', 'R')}
    out['aux'] = {'LP-R': effect(recs, R0, 'LP', 'R'), 'PEAK_V-PEAK': effect(recs, R0, 'PEAK_V', 'PEAK'),
                  'PEAK_V-R': effect(recs, R0, 'PEAK_V', 'R'), 'FIX45-R': effect(recs, R0, 'FIX45', 'R')}
    out['noise5'] = {}
    for p in ['PEAK', 'LP', 'LP_V']:
        E = [effect(recs, {p: red(p, 0.05, s), 'R': red('R', 0.05, s)}, p, 'R') for s in range(5)]
        out['noise5'][p + '-R'] = dict(dS_evt=float(np.mean([e['dS_evt'] for e in E])), seeds=[e['dS_evt'] for e in E])
    # test + test2 합친 PEAK − FIX45 (8절 보조 2). test 값은 result_test.json raw에서 읽는다
    raw = json.load(open(os.path.join(rs.pr.HERE, 'result_test.json'), encoding='utf-8'))['raw']; t1 = rs.record_list('test')
    R1 = {p: np.array([(1 - np.array(raw[f'{p}|{r[0]}'][0]) / np.array(raw[f'U|{r[0]}'][0])) * 100 for r in t1]) for p in ('PEAK', 'FIX45')}
    both = {p: np.r_[R1[p], R0[p]] for p in R1}
    out['pooled_PEAK-FIX45'] = effect(t1 + recs, both, 'PEAK', 'FIX45')
    json.dump(out, open(os.path.join(rs.pr.HERE, 'result_test2.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f'{len(jobs) + len(recs)} runs {time.time() - t0:.0f}s, {len(recs)}쌍 {out["main"]["PEAK-R"]["n_evt"]}사건')
    for grp in ('main', 'aux'):
        for k, e in out[grp].items():
            print(f"{grp:4s} {k:12s} {e['dS_evt']:+6.2f} [{e['ci95'][0]:+.2f}, {e['ci95'][1]:+.2f}] 사건 {e['n_evt_better']}/{e['n_evt']}"
                  f" 기록 {e['n_rec_better']}/{e['n_rec']} θmax악화 {e['thmax_worse']} θmax평균 {e['thmax_mean']:+.2f}")
    for k, e in out['noise5'].items(): print(f'noise5 {k:8s} {e["dS_evt"]:+.2f}')
    e = out['pooled_PEAK-FIX45']; print(f"pooled PEAK-FIX45 {e['dS_evt']:+.2f} [{e['ci95'][0]:+.2f}, {e['ci95'][1]:+.2f}] {e['n_evt']}사건")


if __name__ == '__main__':
    add(sys.argv[2:]) if sys.argv[1] == 'add' else run()
