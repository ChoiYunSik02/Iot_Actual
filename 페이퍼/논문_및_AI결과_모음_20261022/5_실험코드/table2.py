# -*- coding: utf-8 -*-
"""Table 2: 기록 목록 (원문 PGA, 35 cm/s2 정규화 후 주파수 성분, Arias 구간)."""
import numpy as np, records as R
raw=[]
_orig=R._pair
def cap(xx,yy,dtx,dty,dt,tail):
    raw.append((np.abs(xx).max()*100, np.abs(yy).max()*100))   # cm/s2
    return _orig(xx,yy,dtx,dty,dt,tail)
R._pair=cap
P,_=R.paper_pairs(); H=R.held_pairs()
rows=[(f'PEER {n} {s}',x,y) for n,s,x,y in P]+[(n,x,y) for n,x,y in H]
ev=['Imperial Valley 1979']*5+['Northridge 1994','Kobe 1995','Chi-Chi 1999','El Centro 1940','Pohang 2017','Gyeongju 2016']
def dom(a,dt=0.01):
    f=np.fft.rfftfreq(len(a),dt); A=np.abs(np.fft.rfft(a)); m=(f>=0.1)&(f<=5); return f[m][np.argmax(A[m])]
def arias(x,y,dt=0.01):
    c=np.cumsum(x**2+y**2); c/=c[-1]; return np.argmax(c>=.05)*dt, np.argmax(c>=.95)*dt
print('| Record | Earthquake | PGA X/Y before scaling (cm/s²) | Dominant f X/Y (Hz) | Arias 5–95% (s) |\n|---|---|---|---|---|')
for (nm,x,y),e,(px,py) in zip(rows,ev,raw):
    a=arias(x,y); print(f'| {nm} | {e} | {px:.0f} / {py:.0f} | {dom(x):.2f} / {dom(y):.2f} | {a[0]:.0f}–{a[1]:.0f} |')
