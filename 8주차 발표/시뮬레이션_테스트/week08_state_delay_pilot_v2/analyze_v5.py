# 비학습 대조군 결과 분석 (읽기 전용). 사용: python analyze_v5.py <results 폴더> <출력 폴더>
import csv,sys,collections,statistics as st,os,json
res=sys.argv[1]; out=sys.argv[2]; os.makedirs(out,exist_ok=True)
A8=['PEER01','PEER02','PEER03','PEER04','PEER11','PEER13','PEER14','PEER15']
cols=['red_ux_max','red_ux_rms','red_uy_max','red_uy_rms','red_th_max','red_th_rms']
def load(tag):
    d={}
    for r in csv.DictReader(open(f'{res}/control_metrics_record_{tag}.csv',encoding='utf-8-sig')): d[(r['record_id'],r['method'])]=r
    return d
def runtime(tag):
    f=f'{res}/../logs/runtime_{tag}.csv'; d={}
    if not os.path.exists(f): return d
    for r in csv.DictReader(open(f,encoding='utf-8-sig')): d[(r['record_id'],r['method'])]=r
    return d
REF=load('V5_SCORER_REF'); R={k[0]:v for k,v in REF.items() if k[1]=='R'}
recs=sorted(R); ev={r:REF[(r,'R')]['event_id'] for r in recs}
def val(d,r,m='J-AI'): return [float(d[(r,m)][c]) for c in cols]
def summ(d,sub):
    imp={r:sum(val(d,r))/6-sum(float(R[r][c]) for c in cols)/6 for r in sub}
    byev=collections.defaultdict(list)
    for r in sub: byev[ev[r]].append(imp[r])
    evd={e:sum(v)/len(v) for e,v in byev.items()}
    viol=[];worst=1e9
    for r in sub:
        v=val(d,r);rr=[float(R[r][c]) for c in cols]
        m=min(v[4]-rr[4],v[5]-rr[5]); worst=min(worst,m)
        if m<-1e-9: viol.append(r)
    return dict(rec_mean=sum(imp.values())/len(sub),ev_mean=sum(evd.values())/len(evd),n_better=sum(1 for x in imp.values() if x>0),n=len(sub),
                viol_rec=len(viol),viol_ev=len({ev[r] for r in viol}),worst=worst,viol=viol,evd=evd,imp=imp)
tags=['V5_SCORER_REF','V5_DET3']+[f'V5_RAND3_S{k}' for k in range(1,6)]
S={}
for t in tags:
    try: d=load(t)
    except FileNotFoundError: print('없음',t); continue
    S[t]={sn:summ(d,sub) for sn,sub in (('A8',A8),('11',recs))}; S[t]['rt']=runtime(t)
lines=[]
def P(s=''): lines.append(s); print(s)
P('## 고정 시간축 비교 (R 대비 6지표 평균 저감률 차, %p; 비틀림 위반 = 최대·RMS 중 R보다 나쁨 1e-9 초과)')
for sn,name in (('A8','공통 8기록·4사건'),('11','전체 11기록·7사건')):
    P(f'\n### {name}'); P('| 방식 | 기록 평균 | 사건 평균 | 개선 기록 | 위반 기록/사건 | 최악 비틀림 차 |'); P('|---|---|---|---|---|---|')
    for t in tags:
        if t not in S: continue
        s=S[t][sn]; P(f"| {t} | {s['rec_mean']:+.2f} | {s['ev_mean']:+.2f} | {s['n_better']}/{s['n']} | {s['viol_rec']}/{s['viol_ev']} | {s['worst']:+.2f} |")
    rs=[S[f'V5_RAND3_S{k}'][sn] for k in range(1,6) if f'V5_RAND3_S{k}' in S]
    if rs:
        P(f"| 무작위 5시드 평균 [최소, 최대] | {st.mean(x['rec_mean'] for x in rs):+.2f} [{min(x['rec_mean'] for x in rs):+.2f}, {max(x['rec_mean'] for x in rs):+.2f}] | {st.mean(x['ev_mean'] for x in rs):+.2f} [{min(x['ev_mean'] for x in rs):+.2f}, {max(x['ev_mean'] for x in rs):+.2f}] | {st.mean(x['n_better'] for x in rs):.1f}/{rs[0]['n']} | 기록 {st.mean(x['viol_rec'] for x in rs):.1f} [{min(x['viol_rec'] for x in rs)}, {max(x['viol_rec'] for x in rs)}] / 사건 {st.mean(x['viol_ev'] for x in rs):.1f} [{min(x['viol_ev'] for x in rs)}, {max(x['viol_ev'] for x in rs)}] | {st.mean(x['worst'] for x in rs):+.2f} [{min(x['worst'] for x in rs):+.2f}, {max(x['worst'] for x in rs):+.2f}] |")
P('\n### 사건별 개선 (11기록, 사건 내 기록 평균, %p)')
evs=sorted({ev[r] for r in recs}); hdr=['방식']+evs; P('| '+' | '.join(hdr)+' |'); P('|'+'---|'*len(hdr))
for t in tags:
    if t in S: P(f'| {t} | '+' | '.join(f"{S[t]['11']['evd'][e]:+.2f}" for e in evs)+' |')
P('\n### 계산시간 (선택 계산 s, 기록별 중앙값의 중앙값 / p95 최대 / 최대; 실행 환경 변동 있음, 제어 결과에는 고정 시간축이라 영향 없음)')
P('| 방식 | 총 wall(s) | select_s 중앙값 | select_s p95 최대 | select_s 최대 |'); P('|---|---|---|---|---|')
for t in tags:
    if t not in S or not S[t]['rt']: continue
    rr=[v for k,v in S[t]['rt'].items() if k[1]=='J-AI']
    P(f"| {t} | {sum(float(v['wall_s']) for v in rr):.0f} | {st.median(float(v['select_s_median']) for v in rr):.3f} | {max(float(v['select_s_p95']) for v in rr):.3f} | {max(float(v['select_s_max']) for v in rr):.3f} |")
# 점수망 vs 비학습 (사건별 짝 비교)
P('\n### 점수망(V5_SCORER_REF) − 비학습 (사건 평균 차, 11기록)')
for t in tags[1:]:
    if t in S:
        diffs={e:S['V5_SCORER_REF']['11']['evd'][e]-S[t]['11']['evd'][e] for e in evs}
        P(f"- {t}: 사건 평균 차 {st.mean(diffs.values()):+.2f}, 점수망이 더 나은 사건 {sum(1 for x in diffs.values() if x>0)}/{len(diffs)}")
# 재현 확인: 무작위 시드 8401 = 기존 V4_B_RAND3, R = 기존 V4_FOLLOWUP_R
try:
    old=load('V4_B_RAND3'); new=load('V5_RAND3_S1'); mx=max(abs(float(old[(r,'J-AI')][c])-float(new[(r,'J-AI')][c])) for r in recs for c in cols)
    P(f'\n- 재현 확인: V5_RAND3_S1(seed 8401) vs 기존 V4_B_RAND3 최대 차 {mx:.3e}')
    oR=load('V4_FOLLOWUP_R'); mx=max(abs(float(oR[(r,'R')][c])-float(R[r][c])) for r in recs for c in cols)
    P(f'- 재현 확인: V5_SCORER_REF의 R vs 기존 V4_FOLLOWUP_R 최대 차 {mx:.3e}')
    mx=max(abs(float(oR[(r,'J-AI')][c])-float(REF[(r,'J-AI')][c])) for r in recs for c in cols)
    P(f'- 재현 확인: V5_SCORER_REF의 J-AI(기존 점수망) vs 기존 V4_FOLLOWUP_R J-AI 최대 차 {mx:.3e}')
except Exception as e: P(f'재현 확인 생략: {e}')
open(f'{out}/V5_results.md','w',encoding='utf-8').write('\n'.join(lines))
