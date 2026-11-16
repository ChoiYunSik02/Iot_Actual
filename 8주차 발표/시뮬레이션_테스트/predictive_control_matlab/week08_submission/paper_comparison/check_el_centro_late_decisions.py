# -*- coding: utf-8 -*-
"""v3 검토: El Centro J-AI의 실측 지연 1차(JC)와 2차(JCA) 차이를 지령 로그에서 확인한다 (새 계산 없음).
비교 대상 로그: logs/command_timeline_JC_actual.csv (1차), logs/command_timeline_JC_actual_all_actualall.csv (2차), logs/command_timeline_JC_fixed_all.csv (고정 시간축)
확인하는 것은 로그 차이이며, 같은 늦은 결정만 재현하는 지연 패턴 재생 실행은 하지 않았으므로 성능 차이의 원인을 확정하지 않는다.
"""
import csv, os
MAT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
def load(f):
    return [r for r in csv.DictReader(open(os.path.join(MAT, 'logs', f), encoding='utf-8')) if r['record_id'] == 'ElCentro_1940' and r['method'] == 'J-AI']
runs = {'1차(JC)': load('command_timeline_JC_actual.csv'), '2차(JCA)': load('command_timeline_JC_actual_all_actualall.csv'), '고정 시간축(JCX)': load('command_timeline_JC_fixed_all.csv')}
key = lambda r: (r['apply_time'], r['is_pump_angle'], r['is_valve'])
for nm, x in runs.items():
    late = [r for r in x if r['fallback_reason'] == 'deadline' or r['deadline_miss'] == '1']
    print(f'{nm}: 결정 행 {len(x)}개, 마감 초과(deadline) {len(late)}개')
    for r in late:
        print(f"    결정 {float(r['sim_time']):.2f} s → 적용 예정 {float(r['apply_time']):.2f} s, 선택 계산 {float(r['calculation_seconds']):.3f} s (예산 0.27 s), 사유 {r['fallback_reason']}")
def diff(x, y):
    dy = {key(r): r for r in y}; out = []
    for r in x:
        o = dy.get(key(r))
        if o is None: continue
        for c in ('commanded_f', 'commanded_theta', 'commanded_kappa'):
            a, b = r[c], o[c]
            if a == b or (a == 'NaN' and b == 'NaN'): continue
            try:
                if abs(float(a) - float(b)) < 1e-9: continue
            except ValueError: pass
            out.append(float(r['apply_time'])); break
    return sorted(out)
d12 = diff(runs['1차(JC)'], runs['2차(JCA)']); d23 = diff(runs['2차(JCA)'], runs['고정 시간축(JCX)'])
print(f'지령이 다른 적용 격자: 1차 대 2차 {len(d12)}개 (첫 적용 {d12[0]:.2f} s), 2차 대 고정 시간축 {len(d23)}개')
print('결과: 2차와 고정 시간축은 지령이 모두 같고, 1차는 첫 마감 초과 결정의 적용 격자(5.20 s)부터 달라진다.')
print('한계: 늦은 결정 2개만 같은 시각에 재현해 보는 지연 패턴 재생은 하지 않았다. 로그 차이는 확인했으나 성능 차이(+0.71 대 +4.65 %p)의 단일 원인으로 확정하지 않는다.')
