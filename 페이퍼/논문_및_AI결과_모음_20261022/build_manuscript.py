# -*- coding: utf-8 -*-
"""2_원고_섹션별/*.md -> 1_논문초안/논문_초안_v3.md / .docx  (초안 메모 제거, 그림 삽입, 표지·저자, 논문 서식)
사용: 이 폴더에서 `python build_manuscript.py`  (pandoc 필요: pip install pypandoc_binary)
"""
import re, os, tempfile
import pypandoc
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SRC, IMG, OUT = '2_원고_섹션별', '3_그림', '1_논문초안/논문_초안_v3'

# ── 표지 (여기만 고치면 됨) ──
TITLE = 'Pre-setting a rotating semi-active tuned liquid column damper from early ground motion'
AUTHORS = [('Jungju Park', '1', '†'), ('Yun Sik Choi', '1', '†'), ('Jae-Hoon Jeong', '1', '*')]
AFFIL = ['¹ Department of Embedded Software, Kunsan National University, Gunsan 54150, Republic of Korea']
NOTES = ['† These authors contributed equally to this work (co-first authors). '
         'E-mail: jungju3756@naver.com (J. Park), dbstlr6676@naver.com (Y.S. Choi)',
         '* Corresponding author: Jae-Hoon Jeong, jh7129@kunsan.ac.kr']

cap = {}
for m in re.finditer(r'\*\*Fig\. (\d)\.\*\* (.+)', open(f'{SRC}/7_figure_captions_v1.md', encoding='utf-8').read()):
    cap[int(m.group(1))] = m.group(2).strip()
img = {1: 'figG1_spectra.png', 2: 'figG2_response.png', 3: 'figG4_values.png', 4: 'figG6_per_record.png', 5: 'figG8_scoremap.png', 6: 'figG7_ai_vs_fixed.png'}
def fig(n, lead=''):
    return (f'{lead}\n\n' if lead else '') + f'![**Fig. {n}.** {cap[n]}]({IMG}/{img[n]}){{width=6.0in}}\n\n'
secs = ['0_abstract_intro_v1', '1_introduction_v1', '2_model', '3_validation_v1', '4_headroom_v1', '5_prediction_v1', '6_conclusions_v1', '8_references_v1']
out = []
for n in secs:
    t = open(f'{SRC}/{n}.md', encoding='utf-8').read()
    lines = [l for l in t.split('\n') if not (l.startswith('> Draft') or l.startswith('*TODO') or l.startswith('*Note') or l.startswith('*Author initials') or l.strip() == '---')]
    t = '\n'.join(lines)
    if n == '3_validation_v1':
        t = t.replace('\n\n## 3.2', '\n\n' + fig(1, 'The spectra of the eleven pairs are shown in Fig. 1; the share of the spectral energy between 0.25 and 0.45 Hz (around the building frequency of 0.337 Hz) relative to 0.1–5 Hz ranges from 0.6% (Gyeongju 2016) and 0.7% (KJMA) to 15% (Brawley Airport) and 9% (El Centro Array #3).') + '## 3.2', 1)
    if n == '4_headroom_v1':
        a = fig(2, 'Figure 2 shows the roof response of the El Centro 1940 record: the controlled displacement is reduced mostly around the first-mode frequency, where the uncontrolled spectrum has its peak (Fig. 2b), and both RS-TLCD variants reduce the six indices (Fig. 2c). Figure 3 shows how the three actuators move in the same run: the constant setting keeps the frequency and the angle fixed, whereas the original logic changes them every 2.6 s, in step with a response that has already occurred. Figure 4 gives the mean reduction of every record.') + fig(3) + fig(4)
        t = t.replace('\n## 4.3', '\n' + a + '## 4.3', 1)
        t = t.replace('\n## 4.4', '\n' + fig(5, 'Figure 5 shows the mean reduction over the eleven records for all 49 constant settings.') + '## 4.4', 1)
    if n == '5_prediction_v1':
        t = t.replace('\n## 5.6', '\n' + fig(6, 'Figure 6 summarises Table 8 at the earthquake level.') + '## 5.6', 1)
    out.append(t.strip() + '\n')
md = '\n\n'.join(out)
md = re.sub(r'\\tag\{(\d+)[^}]*\}', r'\\qquad (\1)', md)
open(f'{OUT}.md', 'w', encoding='utf-8').write(md)
tmp = os.path.join(tempfile.gettempdir(), 'ms_v3.docx')
pypandoc.convert_file(f'{OUT}.md', 'docx', format='markdown+tex_math_dollars+pipe_tables+implicit_figures',
                      outputfile=tmp, extra_args=['--resource-path=.'])

# ── 후처리: 논문 서식 ──
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
d = docx.Document(tmp)
BLACK = RGBColor(0, 0, 0)

def font(st, size=None, bold=None, italic=None):
    st.font.name = 'Times New Roman'; st.font.color.rgb = BLACK
    rpr = st.element.get_or_add_rPr(); rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs'): rf.set(qn(a), 'Times New Roman')
    rf.set(qn('w:eastAsia'), 'Batang')
    for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        rf.attrib.pop(qn(a), None)
    if size: st.font.size = Pt(size)
    if bold is not None: st.font.bold = bold
    if italic is not None: st.font.italic = italic

names = [s.name for s in d.styles]
for nm in ('Normal', 'Body Text', 'First Paragraph', 'Compact'):
    if nm in names: font(d.styles[nm], 12)
for nm, sz in (('Heading 1', 14), ('Heading 2', 12), ('Heading 3', 12)):
    if nm in names:
        font(d.styles[nm], sz, bold=True, italic=False)
        pf = d.styles[nm].paragraph_format; pf.space_before = Pt(18 if nm == 'Heading 1' else 12); pf.space_after = Pt(6); pf.keep_with_next = True
for nm in ('Image Caption', 'Caption', 'Table Caption'):
    if nm in names:
        font(d.styles[nm], 10, italic=False); d.styles[nm].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

for p in d.paragraphs:
    pf = p.paragraph_format
    if p.style.name.startswith('Heading'):
        continue
    if p.style.name in ('Captioned Figure', 'Figure'):
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER; pf.keep_with_next = True; continue
    if p.style.name in ('Image Caption', 'Caption'):
        pf.line_spacing = 1.0; pf.space_after = Pt(12); continue
    if p.text.startswith('Table ') and re.match(r'Table \d+\.', p.text):      # 표 제목: 표 위, 10pt, 표와 붙임
        pf.keep_with_next = True; pf.line_spacing = 1.0; pf.space_before = Pt(12); pf.space_after = Pt(4)
        for r in p.runs: r.font.size = Pt(10)
        continue
    pf.line_spacing = 1.5
    if p.text and not p.text.startswith('**'):
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

sec = d.sections[0]; sec.page_width = Inches(8.27); sec.page_height = Inches(11.69); sec.left_margin = sec.right_margin = Inches(1); sec.top_margin = sec.bottom_margin = Inches(1)
W = sec.page_width - sec.left_margin - sec.right_margin
for tb in d.tables:
    tb.style = d.styles['Table Grid'] if 'Table Grid' in names else tb.style
    tb.alignment = 1
    n = len(tb.columns); tb.autofit = False
    tblPr = tb._tbl.tblPr
    w = tblPr.find(qn('w:tblW'))
    if w is None:
        w = OxmlElement('w:tblW'); st = tblPr.find(qn('w:tblStyle'))
        (st.addnext(w) if st is not None else tblPr.insert(0, w))
    w.set(qn('w:w'), str(int(W / 635))); w.set(qn('w:type'), 'dxa')
    first = int(W * (0.30 if n > 4 else 0.40)); rest = int((W - first) / max(n - 1, 1))
    for gc, wd in zip(tb._tbl.tblGrid.findall(qn('w:gridCol')), [first] + [rest] * (n - 1)): gc.set(qn('w:w'), str(int(wd / 635)))
    for i, row in enumerate(tb.rows):
        for j, c in enumerate(row.cells):
            c.width = first if j == 0 else rest
            for p in c.paragraphs:
                p.paragraph_format.line_spacing = 1.0; p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.size = Pt(9); r.font.name = 'Times New Roman'
                    if i == 0: r.font.bold = True

# 줄 번호 (심사용 원고), 쪽 번호
ln = OxmlElement('w:lnNumType'); ln.set(qn('w:countBy'), '1'); ln.set(qn('w:restart'), 'continuous'); ln.set(qn('w:distance'), '360')
sp = sec._sectPr; pg = sp.find(qn('w:pgSz')); (pg.addprevious(ln) if pg is not None else sp.append(ln))
fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run()
for tag, txt in (('begin', None), (None, 'PAGE'), ('end', None)):
    if tag:
        e = OxmlElement('w:fldChar'); e.set(qn('w:fldCharType'), tag)
    else:
        e = OxmlElement('w:instrText'); e.set(qn('xml:space'), 'preserve'); e.text = txt
    r._r.append(e)

# 표지: 제목 · 저자 · 소속 · 동등 기여 · 교신저자 → 쪽 나눔 → Abstract
first_p = d.paragraphs[0]
def before(text='', size=12, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.CENTER, after=6):
    p = first_p.insert_paragraph_before(); p.paragraph_format.alignment = align; p.paragraph_format.space_after = Pt(after); p.paragraph_format.line_spacing = 1.15
    if text:
        rr = p.add_run(text); rr.font.size = Pt(size); rr.bold = bold; rr.italic = italic; rr.font.name = 'Times New Roman'
    return p
before(TITLE, 16, bold=True, after=18)
pa = before(after=12)
for k, (nm, aff, mark) in enumerate(AUTHORS):
    rr = pa.add_run(nm); rr.font.size = Pt(12); rr.font.name = 'Times New Roman'
    s = pa.add_run(aff + mark); s.font.superscript = True; s.font.size = Pt(12)
    if k < len(AUTHORS) - 1: pa.add_run(', ').font.size = Pt(12)
for a in AFFIL: before(a, 11, italic=True, after=12)
for nt in NOTES: before(nt, 10, align=WD_ALIGN_PARAGRAPH.LEFT, after=2)
before().add_run().add_break(WD_BREAK.PAGE)

d.core_properties.title = TITLE; d.core_properties.author = ', '.join(a[0] for a in AUTHORS)
d.save(f'{OUT}.docx')
print('ok', len(md.split()), 'words ->', f'{OUT}.docx')
