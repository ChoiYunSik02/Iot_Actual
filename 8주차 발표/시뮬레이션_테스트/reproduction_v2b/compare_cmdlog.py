"""S-TLCD 명령 로그 대조. 기준(실행 전 고정): 결정 시각(스텝 번호) 완전 일치, kappa 값 완전 일치, 진동수 명령 차이 1e-9 Hz 이하."""
import pandas as pd, numpy as np
m=pd.read_csv('matlab_v2b_cmdlog.csv'); p=pd.read_csv('py_v2b_cmdlog.csv')
print('행 수 MATLAB',len(m),'Python',len(p))
key=['rec','type','step0']
mm=m.merge(p,on=key,how='outer',suffixes=('_m','_p'),indicator=True)
print('한쪽에만 있는 결정:', (mm['_merge']!='both').sum())
b=mm[mm['_merge']=='both']
f=b[b.type==1]; k=b[b.type==2]
df=np.abs(f[['v1_m','v2_m']].values-f[['v1_p','v2_p']].values).max()
nk=int((k[['v1_m','v2_m']].values!=k[['v1_p','v2_p']].values).sum())
print(f'진동수 명령 {len(f)}회 × 2방향: 최대 차이 {df:.2e} Hz → {"합격" if df<=1e-9 else "불합격"}')
print(f'kappa 명령 {len(k)}회 × 2방향: 불일치 {nk}건 → {"합격" if nk==0 else "불합격"}')
