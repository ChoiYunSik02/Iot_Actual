import numpy as np, itertools
from tlcd3 import *
from paper_tables import UNC,PAS
L0=2*G/(2*np.pi*F0)**2; lam=0.231; Av=MD/(RHO*L0); Ah=Av/lam; dl=delta(lam,0.4); kd=MD*(2*np.pi*F0)**2
coef={'eq24':0.5*RHO*Av**2/Ah*dl,'eq7':0.5*RHO*Ah*dl}
R=load_records(); unc=np.load('best_unc.npy'); red_p=(1-PAS/UNC)*100
cache={}
for dc,rf,cn in itertools.product([False,True],[False,True],['eq24','eq7']):
    c=coef[cn]; cf=lambda vr,va,c=c: c*np.abs(vr)*vr
    out=[]
    for ax,ay,dt in R:
        k=(dt,dc,rf)
        if k not in cache: cache[k]=make(dt,kd,dc,rf)
        out.append(metrics(run(ax,ay,dt,cache[k],cf)))
    out=np.array(out); rel=(out/PAS-1)*100; red=(1-out/unc)*100
    print(f"devcouple={dc!s:5s} rayleigh_full={rf!s:5s} {cn:4s} mean|rel|={np.abs(rel).mean():5.2f}%  red={np.round(red.mean(0),1)}")
    np.save(f'pas3_{int(dc)}{int(rf)}_{cn}.npy',out)
print('paper red',np.round(red_p.mean(0),1))
