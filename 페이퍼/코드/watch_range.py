# -*- coding: utf-8 -*-
"""exp_range.py 진행 상황 페이지: results/exp_range.log를 10초마다 읽어 results/exp_range_progress.html로 씀.
사용: python watch_range.py  (exp_range.py와 같은 기본 인자 기준. 끝나면 스스로 종료)
"""
import html, os, re, time
import rstlcd as R

LOG, OUT = 'results/exp_range.log', 'results/exp_range_progress.html'
RANGES, KS, DF, NREC = (0.05, 0.1, 0.2), (0.81, 1.0, 1.21), 0.0057, 11
PLAN = [(p, k, NREC * ((round(2 * p * R.F0 / DF) + 1) * 7 + 2)) for p in RANGES for k in KS]   # (범위, 강성, 시뮬레이션 수)
TOTAL = sum(n for *_, n in PLAN)
PAT = re.compile(r'±(\d+)% · 강성 ×([\d.]+) \((\d+)회 (\d+)s\): 원문 RS ([\d.-]+) · 최선 고정 ([\d.-]+) \(([^)]*)\) · '
                 r'Oracle ([\d.-]+) · 여지 ([\d.-]+)%p')


def page(rows, t_start, finished):
    done = sum(int(r[2]) for r in rows); sec = sum(int(r[3]) for r in rows)
    rate = done / sec if sec else 0
    eta = (TOTAL - done) / rate if rate else float('nan')
    fmt = lambda s: '—' if s != s else f'{int(s // 60)}분 {int(s % 60)}초'
    mx = max([float(r[8]) for r in rows] + [1.0])
    body = ''.join(
        f'<tr><td>±{r[0]}%</td><td>×{float(r[1]):g} ({R.F0 * float(r[1]) ** 0.5:.4f} Hz)</td><td>{r[4]}</td><td>{r[5]}</td>'
        f'<td>{html.escape(r[6])}</td><td>{r[7]}</td><td><b>{r[8]}</b></td>'
        f'<td><div class="bar" style="width:{160 * max(float(r[8]), 0) / mx:.0f}px"></div></td></tr>' for r in rows)
    todo = ''.join(f'<tr class="mut"><td>±{p * 100:.0f}%</td><td>×{k:g}</td><td colspan="6">대기 ({n}회)</td></tr>'
                   for p, k, n in PLAN[len(rows):])
    pct = 100 * done / TOTAL
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">{'' if finished else '<meta http-equiv="refresh" content="10">'}
<title>조정 범위 점검</title><style>
:root{{--bg:#fff;--fg:#1a1a1a;--mut:#666;--acc:#2f6fdf;--line:#e3e3e3}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16181c;--fg:#e8e8e8;--mut:#9aa;--acc:#6ea0ff;--line:#333}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;max-width:960px;margin:24px auto;padding:0 16px}}
.prog{{height:22px;background:var(--line);border-radius:6px;overflow:hidden}}.prog div{{height:100%;background:var(--acc)}}
.bar{{height:12px;background:var(--acc);border-radius:3px}}table{{border-collapse:collapse;width:100%;margin:8px 0 20px}}
td,th{{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left;font-variant-numeric:tabular-nums}}.mut{{color:var(--mut)}}
.wrap{{overflow-x:auto}}</style></head><body>
<h1>장치 조정 범위 확대 점검 {'— 완료' if finished else ''}</h1>
<p><b>{len(rows)} / {len(PLAN)}</b> 조합 · 시뮬레이션 {done} / {TOTAL}회 ({pct:.0f}%) · 남은 시간 약 {fmt(eta)} · 경과 {fmt(time.time() - t_start)}</p>
<div class="prog"><div style="width:{pct:.1f}%"></div></div>
<p class="mut">갱신 {time.strftime('%H:%M:%S')} · 10초마다 새로 고침 · 조합 하나가 끝날 때마다 표에 한 줄씩 추가</p>
<p><b>여지 = Oracle − 최선 고정값.</b> AI가 지진마다 다르게 맞춰서 얻을 수 있는 최대치입니다. ±5%에서는 0.6~1.3%p였고, 범위를 넓혀 이 값이 커지면 라벨을 다시 만들 가치가 있습니다.</p>
<div class="wrap"><table><tr><th>조정 범위</th><th>건물 강성 (1차 진동수)</th><th>원문 RS</th><th>최선 고정</th><th>고정 칸</th><th>Oracle</th><th>여지 [%p]</th><th></th></tr>
{body}{todo}</table></div></body></html>"""


if __name__ == '__main__':
    t_start = os.path.getctime(LOG) if os.path.exists(LOG) else time.time()
    while True:
        rows = PAT.findall(open(LOG, encoding='utf-8').read()) if os.path.exists(LOG) else []
        finished = len(rows) >= len(PLAN)
        tmp = OUT + '.tmp'; open(tmp, 'w', encoding='utf-8').write(page(rows, t_start, finished)); os.replace(tmp, OUT)
        if finished:
            break
        time.sleep(10)
