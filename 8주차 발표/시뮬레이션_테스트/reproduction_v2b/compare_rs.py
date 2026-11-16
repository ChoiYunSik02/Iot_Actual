"""RS-TLCD Python(rs_ref.py)–MATLAB(run_v2b_rs_check.m) 대조. 판정 기준(실행 전 고정, 2026-10-31 13시):
 - 결정 시점(스텝 번호·종류): 완전 일치
 - 진동수 명령 ≤ 1e-9 Hz, 목표각 ≤ 1e-6°, 식별 진동수 wx·wy ≤ 1e-9 Hz, κ 완전 일치
 - 1초 상태: 실제각 ≤ 1e-6°, 행렬각·적용 진동수 완전 일치(반올림 후 값), 장치 상대변위 차 ≤ 1e-6 × 기록 내 최대
 - 6지표 응답: 최대 상대차 ≤ 1e-6
 넘으면 불합격으로 보고하고 기준을 바꾸지 않는다."""
import pandas as pd, numpy as np, sys
V=sys.argv[1] if len(sys.argv)>1 else 'ABC'
cols8=['rec','type','step0','t','v1','v2','v3','v4']
for v in V:
    try:
        pm=np.load(f'rsref_{v}_metrics.npy'); mm=pd.read_csv(f'matlab_rs_{v}_metrics.csv')[['Xmax','Xrms','Ymax','Yrms','thmax','thrms']].values
    except FileNotFoundError as e: print(v,'파일 없음',e); continue
    pd_=pd.read_csv(f'py_rs_{v}_dec.csv',header=0,names=cols8,usecols=range(8)); md=pd.read_csv(f'matlab_rs_{v}_dec.csv')
    ps=pd.read_csv(f'py_rs_{v}_state.csv'); ms=pd.read_csv(f'matlab_rs_{v}_state.csv')
    out=[]
    dm=np.abs(mm/pm-1).max(); out.append(('6지표 최대 상대차',f'{dm:.1e}',dm<=1e-6))
    j=pd_.merge(md,on=['rec','type','step0'],how='outer',suffixes=('_p','_m'),indicator=True)
    only=int((j['_merge']!='both').sum()); out.append(('한쪽에만 있는 결정',only,only==0))
    b=j[j['_merge']=='both']; f1=b[b.type==1]; f2=b[b.type==2]
    df=np.abs(f1.v1_p-f1.v1_m).max(); out.append(('진동수 명령 최대차(Hz)',f'{df:.1e}',df<=1e-9))
    dth=np.abs(f1.v2_p-f1.v2_m).max(); out.append(('목표각 최대차(°)',f'{dth:.1e}',dth<=1e-6))
    dw=max(np.abs(f1.v3_p-f1.v3_m).max(),np.abs(f1.v4_p-f1.v4_m).max()); out.append(('식별 진동수 최대차(Hz)',f'{dw:.1e}',dw<=1e-9))
    nk=int((f2.v1_p!=f2.v1_m).sum()); out.append((f'κ 불일치(결정 {len(f2)}회)',nk,nk==0))
    s=ps.merge(ms,on=['rec','step0'],suffixes=('_p','_m'))
    da=np.abs(s.theta_act_p-s.theta_act_m).max(); out.append(('실제각 최대차(°)',f'{da:.1e}',da<=1e-6))
    nq=int((np.abs(s.theta_mat_p-s.theta_mat_m)>1e-9).sum()); out.append(('행렬각 불일치',nq,nq==0))
    nf=int((np.abs(s.f_applied_p-s.f_applied_m)>1e-12).sum()); out.append(('적용 진동수 불일치',nf,nf==0))
    rr=0
    for r,g in s.groupby('rec'):
        sc=max(np.abs(g[['rel_x_p','rel_y_p']].values).max(),1e-30); rr=max(rr,np.abs(g[['rel_x_p','rel_y_p']].values-g[['rel_x_m','rel_y_m']].values).max()/sc)
    out.append(('장치 상대변위 최대차/기록 최대',f'{rr:.1e}',rr<=1e-6))
    print(f'== 해석 {v}: 상태 표본 {len(s)}개, 결정 {len(b)}개')
    for a,bv,ok in out: print(f'   {a}: {bv} → {"합격" if ok else "불합격"}')
