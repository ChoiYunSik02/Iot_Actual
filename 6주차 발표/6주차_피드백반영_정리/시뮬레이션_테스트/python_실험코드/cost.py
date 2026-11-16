import numpy as np
import sim
def ratios(m, m0):
    return dict(rms=m[0]/m0[0], late=m[1]/max(m0[1],1e-9), pk=m[2]/m0[2], idr=m[3]/m0[3], acc=m[4]/m0[4],
                ystroke=m[5]/sim.YMAX, hs=m[6]/sim.TEND)
def J(m, m0):
    r = ratios(m, m0)
    late = min(r['late'], 3.0)
    return 0.35*r["rms"] + 0.25*late + 0.25*r["idr"] + 0.15*r["acc"] + 4.0*r["hs"] + 0.1*m[8]
