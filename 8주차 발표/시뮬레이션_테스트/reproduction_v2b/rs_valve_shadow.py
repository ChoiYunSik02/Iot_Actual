"""RS 밸브 판정 두 방식(v2: 합성 후 재사영 / 각 자유도 직접)을 같은 궤적(v2 방식으로 진행) 위에서 동시에 계산해 결정이 갈리는 시점을 센다."""
import numpy as np
from dyn import RS2, sim_rs
from rstlcd_lit import RSLitPlant
from tlcd import load_records
class Shadow(RS2):
    def __init__(s,dt): super().__init__(dt,'step','proj'); s.rec=[]
    def step(s,k,t,o):
        if k>0 and k%s.nc==0:
            c,s_=np.cos(s.th),np.sin(s.th); a=o['atop_abs']; v=o['vrel2']
            vr=c*v[0]+s_*v[1]; p=(vr*c*a[0], vr*s_*a[1]); d=(v[0]*a[0], v[1]*a[1])
            kap=lambda sx,sy: 0.8 if (sx<=0 and sy<=0) else (0.1 if (sx>0 and sy>0) else 0.4)
            s.rec.append((t,np.rad2deg(s.th),kap(*p),kap(*d)))
        return super().step(k,t,o)
tot=dis=0; plants={}; per=[]
for j,(ax,ay,dt) in enumerate(load_records()):
    if dt not in plants: plants[dt]=RSLitPlant(dt)
    c=Shadow(dt); sim_rs(plants[dt],ax,ay,c); r=np.array(c.rec); m=r[:,2]!=r[:,3]
    per.append((j+1,len(r),int(m.sum()))); tot+=len(r); dis+=int(m.sum())
    if j==4:
        print('5번 기록 불일치 결정(시각, 각도, v2 κ, 직접 κ):'); print(np.round(r[m][:12],2))
print('기록별 (결정 수, 불일치):',per)
print(f'전체 {tot}회 중 {dis}회({dis/tot*100:.1f} %) 불일치')
