import numpy as np
from semiactive import *
FREQS=np.linspace(0.05,2.0,391)
def ident(sig,dt,method):
    if len(sig)<8: return F0
    if method.startswith('fft'):
        W=None if method=='fft_all' else float(method.split('_')[1])
        s=sig if W is None else sig[-int(W/dt):]
        s=s-s.mean(); nf=max(2**16,len(s)); S=np.abs(np.fft.rfft(s*np.hanning(len(s)),nf)); f=np.fft.rfftfreq(nf,dt)
        m=(f>=0.05)&(f<=2.0); return f[m][np.argmax(S[m])]
    if method.startswith('morlet'):
        w0=6.0; best=None; t=np.arange(len(sig))*dt; tk=t[-1]
        mags=[]
        for f in FREQS:
            sd=w0/(2*np.pi*f); m=t>=tk-4*sd; tau=t[m]-tk
            psi=np.exp(-1j*2*np.pi*f*tau)*np.exp(-tau**2/(2*sd**2))
            mags.append(np.abs(np.sum(sig[m]*psi))*dt*np.sqrt(f))
        return FREQS[int(np.argmax(mags))]
    if method=='zc':
        s=sig[-int(2.6/dt):]; z=np.sum(np.diff(np.sign(s))!=0); return max(z,1)/(2*2.6)
class STLCD:
    def __init__(self,dt,method,acc='abs',dtf=2.6,dtc=1.0):
        self.dt=dt; self.m=method; self.acc=acc; self.nf=int(round(dtf/dt)); self.nc=int(round(dtc/dt))
        self.hx=[]; self.hy=[]; self.f=[F0,F0]; self.kap=[0.4,0.4]
    def step(self,k,t,o):
        self.hx.append(o['top'][0]); self.hy.append(o['top'][1])
        if k>0 and k%self.nf==0:
            for j,h in enumerate((self.hx,self.hy)):
                w=ident(np.array(h),self.dt,self.m); self.f[j]=min(max(w,FMIN),FMAX)
        if k>0 and k%self.nc==0:
            a=o['atop_abs'] if self.acc=='abs' else o['atop']
            for j in range(2):
                s=o['vrel'][j]*a[j]; self.kap[j]=0.1 if s>0 else 0.8
        return self.f[0],self.f[1],self.kap[0],self.kap[1]
