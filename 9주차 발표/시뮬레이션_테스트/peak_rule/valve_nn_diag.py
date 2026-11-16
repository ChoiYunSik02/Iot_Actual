"""진단 전용: NN_V가 학습은 되는지 본다 (채택 판정 아님, 계획 9절의 NN_V 결과는 그대로 둔다).
사전 등록 설정은 경사 갱신 40회뿐이었다. 여기서는 작은 묶음(6기록)으로 300회 갱신한다.
19사건을 알파벳 순으로 놓고 5번째마다 4사건을 빼서 평가한다. 학습 기록과 빠진 기록의 이득을 함께 본다.
"""
import os, json, time
import numpy as np
import torch
from concurrent.futures import ProcessPoolExecutor
import valve_nn as v
from valve_nn import net, grad, evaluate, EV, recs62, CACHE

UPDATES, BATCH, LR = 300, 6, 3e-3

if __name__ == '__main__':
    recs = recs62(); evs = sorted({EV(r) for r in recs}); hold = set(evs[2::5]); assert len(evs) == 19 and len(hold) == 4
    tr = [j for j, r in enumerate(recs) if EV(r) not in hold]; te = [j for j, r in enumerate(recs) if EV(r) in hold]
    cnt = {e: sum(EV(r) == e for r in recs) for e in evs}; g = np.random.default_rng(8700); t0 = time.time()
    C = {j: np.load(os.path.join(CACHE, f'{j}.npz')) for j in range(len(recs))}; gain = lambda j, m: float(((C[j]['m0'] - np.array(m)) / C[j]['U']).mean() * 100)
    m = net(); opt = torch.optim.Adam(m.parameters(), lr=LR); hist = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for u in range(UPDATES):
            b = g.choice(tr, BATCH, replace=False).tolist(); sd = {k: x.clone() for k, x in m.state_dict().items()}
            R = list(ex.map(grad, [(j, sd) for j in b], chunksize=1)); w = np.array([1 / cnt[EV(recs[j])] for j in b]); w /= w.sum()
            for i, p in enumerate(m.parameters()): p.grad = torch.tensor(sum(wi * r[1][i] for wi, r in zip(w, R)))
            torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step()
            if u % 20 == 0: print(u, round(float(sum(wi * r[0] for wi, r in zip(w, R))), 5), f'{time.time() - t0:.0f}s', flush=True)
            if (u + 1) % 100 == 0:
                sd = {k: x.clone() for k, x in m.state_dict().items()}
                r = dict(ex.map(evaluate, [(j, recs[j], sd) for j in tr + te]))
                ev = lambda js: float(np.mean([np.mean([gain(j, r[j]) for j in js if EV(recs[j]) == e]) for e in sorted({EV(recs[j]) for j in js})]))
                hist.append(dict(update=u + 1, train_gain=ev(tr), held_gain=ev(te), held_events=sorted(hold)))
                print(hist[-1], flush=True)
    json.dump(hist, open('result_valve_nn_diag.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
