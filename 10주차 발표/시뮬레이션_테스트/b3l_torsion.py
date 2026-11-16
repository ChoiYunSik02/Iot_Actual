"""10주차 계획 15.1: b3l 비틀림 최대 악화 원인 분석 (저장된 겹 결과만 사용, 학습·시뮬레이션 없음, test·test2 안 씀).

지표 순서(run_set.metrics): x 최대, x RMS, y 최대, y RMS, 비틀림 최대, 비틀림 RMS.
지표별 개선 %p = (LP_V − 방식) / 무제어 × 100. 사건 가중 평균은 사건 안 평균 후 사건 평균.
결과: results_b2/b3l_torsion/분석.md, result.json
"""
import os, json, glob
import numpy as np
import b0_diag
import valve_nn as vn

HERE = os.path.dirname(os.path.abspath(__file__)); R2 = os.path.join(HERE, 'results_b2')
NAMES = ['x 최대', 'x RMS', 'y 최대', 'y RMS', '비틀림 최대', '비틀림 RMS']


def load_res(part, nf=13):
    res = {}
    for fp in glob.glob(os.path.join(R2, part, f'fold_{nf}_*.json')):
        res.update({int(j): np.array(v) for j, v in json.load(open(fp, encoding='utf-8'))['res'].items()})
    return res


def evw(vals, evof):
    evs = sorted(set(evof.values())); return np.array([np.mean([v for j, v in vals.items() if evof[j] == e]) for e in evs])


def main():
    recs = b0_diag.recs62(); idx = list(range(len(recs))); evof = {j: vn.EV(recs[j]) for j in idx}
    Z = {j: np.load(os.path.join(b0_diag.ORACLE, f'rec_{j:02d}.npz')) for j in idx}
    m0 = {j: Z[j]['m0'] for j in idx}; U = {j: Z[j]['U'] for j in idx}
    runs = {'b3l B3_13': load_res('b3l'), 'b3 B3_13': load_res('b3'), '상한 해(B0\')': {j: Z[j]['m_best'] for j in idx}}
    for k, r in runs.items(): assert len(r) == 62, (k, len(r))
    out, L = {}, ['# 10주차 15.1 b3l 비틀림 최대 악화 분석 (자동 생성, 62쌍 19사건, 저장 결과만)', '',
                  '## 지표별 LP_V 대비 개선 (사건 가중 평균 %p, 양수 = 나아짐)', '',
                  '| 방식 | ' + ' | '.join(NAMES) + ' | 6지표 평균 | 비틀림 최대 악화 쌍 |', '|---' * 9 + '|']
    for k, r in runs.items():
        d = {j: (m0[j] - r[j]) / U[j] * 100 for j in idx}
        per = [evw({j: d[j][i] for j in idx}, evof).mean() for i in range(6)]
        tot = evw({j: d[j].mean() for j in idx}, evof).mean()
        thw = [j for j in idx if r[j][4] > m0[j][4] * (1 + 1e-9)]
        # 악화 크기: 무제어 대비 %p, 그리고 LP_V 대비 상대 %
        mag = np.array([-d[j][4] for j in thw]); rel = np.array([(r[j][4] / m0[j][4] - 1) * 100 for j in thw])
        both = sum(d[j].mean() > 0 for j in thw)
        cor_rms = float(np.corrcoef([d[j][4] for j in idx], [d[j][5] for j in idx])[0, 1])
        cor_tot = float(np.corrcoef([d[j][4] for j in idx], [np.delete(d[j], 4).mean() for j in idx])[0, 1])
        thw_ev = {}
        for j in thw: thw_ev[evof[j]] = thw_ev.get(evof[j], 0) + 1
        out[k] = dict(per_metric=per, mean6=tot, thmax_worse=len(thw), worse_mag_pp_median=float(np.median(mag)) if len(mag) else 0,
                      worse_mag_pp_max=float(mag.max()) if len(mag) else 0, worse_rel_pct_median=float(np.median(rel)) if len(rel) else 0,
                      worse_rel_pct_max=float(rel.max()) if len(rel) else 0, worse_but_mean_better=int(both),
                      corr_thmax_thrms=cor_rms, corr_thmax_other5=cor_tot, worse_by_event=thw_ev)
        L.append(f'| {k} | ' + ' | '.join(f'{v:+.2f}' for v in per) + f' | {tot:+.2f} | {len(thw)} |')
    L += ['', '## 비틀림 최대 악화 크기와 관계', '',
          '| 방식 | 악화 쌍 | 크기 중앙값 %p(무제어 대비) | 최대 %p | LP_V 대비 상대 중앙값 % | 최대 % | 그중 6지표 평균은 나아진 쌍 | 상관: 비틀림 최대 vs 비틀림 RMS | 상관: 비틀림 최대 vs 나머지 5지표 |',
          '|---|---|---|---|---|---|---|---|---|']
    for k, o in out.items():
        L.append(f'| {k} | {o["thmax_worse"]} | {o["worse_mag_pp_median"]:.2f} | {o["worse_mag_pp_max"]:.2f} | {o["worse_rel_pct_median"]:.2f} | {o["worse_rel_pct_max"]:.2f} | {o["worse_but_mean_better"]} | {o["corr_thmax_thrms"]:+.2f} | {o["corr_thmax_other5"]:+.2f} |')
    L += ['', '## 사건별 비틀림 최대 악화 쌍 수 (b3l B3_13)', '', ', '.join(f'{e} {n}' for e, n in sorted(out['b3l B3_13']['worse_by_event'].items(), key=lambda t: -t[1]))]
    od = os.path.join(R2, 'b3l_torsion'); os.makedirs(od, exist_ok=True)
    json.dump(out, open(os.path.join(od, 'result.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(os.path.join(od, '분석.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n'); print('\n'.join(L))


if __name__ == '__main__':
    main()
