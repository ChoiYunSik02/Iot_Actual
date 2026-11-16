# -*- coding: utf-8 -*-
import io
# paper_models.m 에 짧은 이름 추가
s = io.open('paper_models.m', encoding='utf-8').read()
pairs = [("M(k).name  = 'PLOS ONE 2022 (4층 축소모형)';", "PLOS ONE 2022\n축소모형"),
         ("M(k).name  = 'JIPR 2026 (6층 RC 실물)';",      "JIPR 2026\n6층 실물"),
         ("M(k).name  = 'JOBE 2025 (편심 프레임 실물)';",   "JOBE 2025\n편심 실물"),
         ("M(k).name  = '본 연구 3층 (1.20 Hz)';",         "본 연구 3층"),
         ("M(k).name  = '본 연구 장주기 (0.50 Hz)';",       "본 연구 장주기")]
for anchor, short in pairs:
    assert s.count(anchor) == 1, anchor
    s = s.replace(anchor, anchor + "\nM(k).short = sprintf('%s');" % short)
io.open('paper_models.m','w',encoding='utf-8').write(s)

# feasibility_map.m 라벨 로직 교체
f = io.open('feasibility_map.m', encoding='utf-8').read()
old = """    lbl = sprintf('  %s\n  h/D=%.3f (\\mu=%.0f%%)', ...
                  strtok(M(i).name,' ('), M(i).hD, M(i).mu*100);
    ha = 'left';
    if M(i).f1 > 1.1, ha = 'right'; lbl = strrep(lbl, '  ', ''); end
    text(M(i).f1, M(i).Mmod, lbl, 'FontSize',9.5, 'Color',CD, ...
         'HorizontalAlignment', ha, 'VerticalAlignment','middle', 'FontWeight','bold');"""
new = """    lbl = sprintf('%s\nh/D=%.3f  (\\mu=%.0f%%)', M(i).short, M(i).hD, M(i).mu*100);
    if M(i).f1 > 1.05
        ha = 'right'; dx = 0.93; va = 'middle';
    else
        ha = 'left';  dx = 1.07; va = 'middle';
    end
    dy = 1.0;
    if M(i).Mmod < 100, va = 'bottom'; dy = 1.9; end      % 축소모형은 위로
    text(M(i).f1*dx, M(i).Mmod*dy, lbl, 'FontSize',9.5, 'Color',CD, ...
         'HorizontalAlignment', ha, 'VerticalAlignment', va, 'FontWeight','bold', ...
         'BackgroundColor',[1 1 1 ], 'Margin',1.5);"""
assert f.count(old) == 1
f = f.replace(old, new)
io.open('feasibility_map.m','w',encoding='utf-8').write(f)
print('라벨 수정 완료')
