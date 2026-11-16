"""Python 기준 시계열(수동 TLCD, κ=0.4 고정). 감쇠 해석 D0/D3/D4 + 무제어. 입력은 inputs/*.csv 그대로 사용."""
import sys,numpy as np,glob,os
SRC='/home/claude/iot-actuator/페이퍼/코드/'
sys.path.insert(0,SRC)
src=open(SRC+'rstlcd.py',encoding='utf-8').read()
OLD="return c_scale * 0.5 * RHO * self.Av ** 2 / self.Ah * delta(self.kappa, self.lam) * abs(vrel)"
assert OLD in src
var={'D0':OLD,'D3':"return c_scale * 0.5 * RHO * self.Ah * delta(self.kappa, self.lam) * abs(vrel)",'D4':"return c_scale * 0.5 * RHO * self.Av * delta(self.kappa, self.lam) * abs(vrel)"}
mods={}
for k,v in var.items():
    m=type(sys)('R'+k); exec(compile(src.replace(OLD,v),'R'+k,'exec'),m.__dict__); mods[k]=m
here=os.path.dirname(os.path.abspath(__file__))+'/../'
for f in sorted(glob.glob(here+'inputs/PEER*.csv')):
    no=os.path.basename(f)[4:6]; a=np.loadtxt(f,delimiter=','); x,y=a[:,0],a[:,1]
    o=mods['D0'].simulate(x,y,0.01,'none'); np.savetxt(here+f'python_ref/PEER{no}_none.csv',np.c_[o['ux'],o['uy'],o['th']],delimiter=',',fmt='%.17g')
    for k,m in mods.items():
        o=m.simulate(x,y,0.01,'passive',c_scale=1.0)
        np.savetxt(here+f'python_ref/PEER{no}_passive_{k}.csv',np.c_[o['ux'],o['uy'],o['th']],delimiter=',',fmt='%.17g')
    print('done',no,flush=True)
