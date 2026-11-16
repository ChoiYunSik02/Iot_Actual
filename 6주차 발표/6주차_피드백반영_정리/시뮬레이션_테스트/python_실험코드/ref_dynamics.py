import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, sim
from sim import DT, G, N
YMAX=sim.YMAX; XI_OPT=6.0
def go(A,Tp,u,zeta=0.02,fscale=1.0,tlcd=True,tend=24.0):
    K,C,Minv,mf,kf,cnl,Rg=sim.make_system(fscale,zeta,has_tlcd=tlcd)
    x=np.zeros(14); Fv=np.zeros(6); out=np.zeros(14)
    ns=int(tend/DT); roof=np.zeros(ns); ys=np.zeros(ns)
    xi=u*XI_OPT
    def f(x,t):
        ag=A*G*np.sin(2*np.pi*t/Tp) if t<Tp/2 else 0.0
        sim._deriv(x,ag,Fv,xi,0.0,K,C,Minv,kf,cnl,Rg,mf,out); return out.copy()
    for i in range(ns):
        t=i*DT
        k1=f(x,t);k2=f(x+.5*DT*k1,t+.5*DT);k3=f(x+.5*DT*k2,t+.5*DT);k4=f(x+DT*k3,t+DT)
        x=x+DT/6*(k1+2*k2+2*k3+k4); roof[i]=x[5]; ys[i]=x[12]
    return np.max(np.abs(roof)),np.sqrt(np.mean(roof**2)),np.max(np.abs(ys))
rows=[]
for A in (0.5,1.0,1.5):
    for name,u,tl in (("none",1.0,False),("xi3",0.5,True),("xi6",1.0,True),("xi12",2.0,True)):
        pk,rms,ypk=go(A,1.0,u,tlcd=tl); rows.append((A,name,pk,rms,ypk))
        print(f"{A},{name},{pk:.6e},{rms:.6e},{ypk:.6e}")
np.savetxt('ref.csv',[(r[0],{"none":0,"xi3":3,"xi6":6,"xi12":12}[r[1]],r[2],r[3],r[4]) for r in rows],delimiter=',',header='A_g,xi,roofpeak_m,roofrms_m,ypeak_m',comments='')
print(sim.MFLOOR,sim.KFLOOR,sim.MU*sim.MEFF)
