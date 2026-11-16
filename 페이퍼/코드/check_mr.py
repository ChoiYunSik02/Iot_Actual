# -*- coding: utf-8 -*-
"""2번 사전 점검: 조기경보 정보(규모 M, 거리 R, 지반 등급)만으로 고정값보다 나은 칸을 고를 수 있나?
라벨 점수 지도만 씀 (시뮬레이션 없음), 5분할 교차 검증. 입력별로 비교: 건물 진동수만 / + M·R·지반
사용: TLCD_SOURCE=mr python check_mr.py   (라벨: TLCD_SOURCE=mr python gen_labels.py --n 1000)
"""
import glob, json, os
import numpy as np
from gen_labels import OUT
from train_ai import train, DEV, torch

S, X = [], []
for p in sorted(glob.glob(os.path.join(OUT, 's*.npz'))):
    d = np.load(p); m = json.loads(str(d['meta'])); S.append(d['score'].ravel())
    X.append([np.sqrt(m['k_scale']) - 1, m['M'], np.log(m['R']), *np.eye(3)[m['site']]])
S, X = np.array(S), np.array(X, np.float32); Y = (S - S.mean(1, keepdims=True)).astype(np.float32)
fold = np.random.default_rng(0).integers(0, 5, len(S))
res = {n: np.zeros(len(S)) for n in ('fixed', 'k', 'k+M·R·site')}
for f in range(5):
    tr, te = fold != f, fold == f
    res['fixed'][te] = S[te, S[tr].mean(0).argmax()]
    for name, cols in (('k', [0]), ('k+M·R·site', slice(None))):
        model, mu, sd, _ = train(X[tr][:, cols], Y[tr], 300, seed=f)
        with torch.no_grad():
            out = model(torch.tensor((X[te][:, cols] - mu) / sd, device=DEV)).cpu().numpy()
        res[name][te] = S[te][np.arange(te.sum()), out.argmax(1)]
orc = S.max(1)
print(f'샘플 {len(S)}개 · 6개 지표 평균 저감률 [%]')
for g, w in [('전체', np.ones(len(S), bool)), ('R < 50 km', X[:, 2] < np.log(50)), ('R ≥ 100 km', X[:, 2] >= np.log(100))]:
    print(f'{g:10s} ({w.sum():4d}) ' + ' · '.join(f'{n} {v[w].mean():.2f}' for n, v in res.items()) + f' · Oracle {orc[w].mean():.2f}'
          + f' · 여지 회수 {(res["k+M·R·site"][w].mean() - res["fixed"][w].mean()) / (orc[w].mean() - res["fixed"][w].mean()) * 100:.0f}%')
