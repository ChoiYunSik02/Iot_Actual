import sys, os, json
sys.path.insert(0, os.getcwd())
import numpy as np, scipy.io as sio
import run_set as rs
from run_set import load
X = sys.argv[1]; recs = rs.record_list('paper15') + rs.record_list('dev'); assert len(recs) == 33
R = {}
for j, r in enumerate(recs):
    ax, ay, dt = load(r); R[f'r{j}'] = dict(agx=ax, agy=ay, dt=dt)
sio.savemat(os.path.join(X, 'recs.mat'), R)
json.dump([[r[0], r[1]] for r in recs], open(os.path.join(X, 'ids.json'), 'w'))
print(sum(len(R[k]['agx']) for k in R))
