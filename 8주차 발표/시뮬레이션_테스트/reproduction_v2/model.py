import numpy as np, re, glob, scipy.linalg as sl
N=30; m=9.216e5; J=2.797e8
kx=np.full(N,1.6213e9); kx[0]=1.021e9
kt=np.full(N,5.0261e11); kt[0]=3.1651e11
ex,ey=6.0,2.0
def shear(k):
    K=np.zeros((N,N))
    for i in range(N):
        K[i,i]+=k[i]
        if i+1<N: K[i,i]+=k[i+1]; K[i,i+1]-=k[i+1]; K[i+1,i]-=k[i+1]
    return K
def build(variant='cm'):
    Kx=shear(kx); Ky=shear(kx); Kt=shear(kt)
    M=np.diag(np.r_[np.full(N,m),np.full(N,m),np.full(N,J)])
    K=np.zeros((3*N,3*N))
    K[:N,:N]=Kx; K[N:2*N,N:2*N]=Ky
    if variant=='cm':   # 강성중심 오프셋을 질량중심 기준으로 정식 변환
        K[:N,2*N:]=-Kx*ey; K[2*N:,:N]=-Kx*ey
        K[N:2*N,2*N:]=Ky*ex; K[2*N:,N:2*N]=Ky*ex
        K[2*N:,2*N:]=Kt+ey**2*Kx+ex**2*Ky
    else:              # 논문 식 19 문자 그대로: Ktheta 그대로
        K[:N,2*N:]=Kx*ey; K[2*N:,:N]=Kx*ey
        K[N:2*N,2*N:]=Ky*ex; K[2*N:,N:2*N]=Ky*ex
        K[2*N:,2*N:]=Kt
    return M,K
def freqs(M,K):
    w2=sl.eigh(K,M,eigvals_only=True); return np.sqrt(np.abs(w2))/2/np.pi
def uncoupled():
    Kx=shear(kx); return np.sqrt(sl.eigh(Kx,np.eye(N)*m,eigvals_only=True))/2/np.pi
