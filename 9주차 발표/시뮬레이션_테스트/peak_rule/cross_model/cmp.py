import sys, os, json, csv
sys.path.insert(0, os.getcwd())
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled, Tracked, Peak
P = {'R': Tracked, 'PEAK': Peak}
def job(a):
    p, j, r = a; ax, ay, dt = load(r)
    if p == 'U': return p, j, uncontrolled(ax, ay, dt).tolist()
    return p, j, metrics(simulate(Plant(dt), ax, ay, P[p](dt))[0]).tolist()
if __name__ == '__main__':
    X = sys.argv[1]; recs = rs.record_list('paper15') + rs.record_list('dev')
    T = {}
    for row in csv.reader(open(os.path.join(X, 'out.csv'))): T[(row[1], int(row[0]))] = np.array(row[2:], float)
    with ProcessPoolExecutor(max_workers=12) as ex:
        M = {(p, j): np.array(m) for p, j, m in ex.map(job, [(p, j, r) for p in ('U', 'R', 'PEAK') for j, r in enumerate(recs)])}
    ev = lambda r: r[1].replace(',', '').split()[0]; evs = sorted({ev(r) for r in recs}); n = len(recs)
    def rep(D, name):
        red = {p: np.array([(1 - D[(p, j)] / D[('U', j)]) * 100 for j in range(n)]) for p in ('R', 'PEAK')}
        d = (red['PEAK'] - red['R']).mean(1); de = np.array([d[[j for j in range(n) if ev(recs[j]) == e]].mean() for e in evs])
        th = sum(D[('PEAK', j)][4] > D[('R', j)][4] + 1e-12 for j in range(n))
        print(name, 'R %.2f PEAK %.2f' % (red['R'].mean(), red['PEAK'].mean()), 'PEAK-R evt %+.2f CI %s rec %+.2f better %d/%d events>0 %d/%d thmax_worse %d' % (de.mean(), np.round(rs.boot_ci(de), 2).tolist(), d.mean(), (d > 0).sum(), n, (de > 0).sum(), len(evs), th))
        print('   per-event', dict(zip(evs, np.round(de, 2).tolist())))
        return d, red
    a, ra = rep(M, 'mine (D0-A)'); b, rb = rep(T, 'teammate (rstlcd_sim)')
    print('per-record corr PEAK-R gain %.3f, R reduction corr %.3f' % (np.corrcoef(a, b)[0, 1], np.corrcoef(ra['R'].mean(1), rb['R'].mean(1))[0, 1]))
    print('paper15 only: mine %+.2f teammate %+.2f' % (a[:15].mean(), b[:15].mean()))
    print('U roof X max ratio teammate/mine median', np.median([T[('U', j)][0] / M[('U', j)][0] for j in range(n)]).round(4))
    json.dump(dict(ids=[r[0] for r in recs], mine=a.tolist(), teammate=b.tolist()), open(os.path.join(X, 'cmp.json'), 'w'))
