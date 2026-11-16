# -*- coding: utf-8 -*-
"""1_논문초안/논문_초안_v3.md -> 1_논문초안/논문_SSS_투고본.docx  (Techno-Press 양식, Smart Structures and Systems)
양식: ../TP_Template(2026).docx 를 그대로 열어 표지(제목·저자·소속·초록·키워드)를 채우고 본문을 갈아 끼움.
규정: https://www.techno-press.com/documents/authors-guide
  본문 Times New Roman 11 pt, 첫 줄 0.5 cm 들여쓰기 · 1단계 제목 Arial 11 bold · 2단계 Arial 11, 0.5 cm 들여쓰기
  그림 캡션 "Figure N." 아래 가운데 · 표 캡션 "Table N." 위 · 캡션·표 TNR 10 · 식 가운데, 번호 오른쪽
  인용 [1] 번호식(등장 순), 번호·그림·식 참조 숫자는 파란색 · 참고문헌 APA, TNR 10, 번호 목록
사용: 이 폴더에서 `python build_tp.py` (먼저 build_manuscript.py로 v3 md를 만들어 둘 것)
"""
import copy, os, re, tempfile, zipfile
import pypandoc
import docx
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from lxml import etree

os.chdir(os.path.dirname(os.path.abspath(__file__)))
SRC, TPL, OUT = '1_논문초안/논문_초안_v3.md', '../TP_Template(2026).docx', '1_논문초안/논문_SSS_투고본.docx'

TITLE = 'Pre-setting a rotating semi-active tuned liquid column damper from early ground motion'
RUN_AUTH = 'J. Park, Y.S. Choi and J.-H. Jeong'
AFFIL = 'Department of Embedded Software, Kunsan National University, 558 Daehak-ro, Gunsan 54150, Republic of Korea'
CORR = 'Corresponding author, Professor, E-mail: jh7129@kunsan.ac.kr'
EQUAL = (' These authors contributed equally to this work (co-first authors), '
         'E-mail: jungju3756@naver.com (J. Park), dbstlr6676@naver.com (Y.S. Choi)')
KEYWORDS = ('early ground-motion information; leave-one-earthquake-out; neural network; semi-active control; '
            'torsional coupling; tuned liquid column damper')

# 본문의 저자-연도 인용 → 번호 (등장 순)
CITE = [('Fu et al. (2025)', 'Fu et al. [1]'), ('Fu et al. 2025', 'Fu et al. [1]'),
        ('Wang et al. (2022)', 'Wang et al. [2]'), ('Kim and Kim (2023)', 'Kim and Kim [3]'),
        ('AlHamaydeh et al. (2024)', 'AlHamaydeh et al. [4]'), ('Farsijani et al. (2025)', 'Farsijani et al. [5]'),
        ('Kanai–Tajimi spectrum with Clough–Penzien high-pass filtering', 'Kanai–Tajimi spectrum [6, 7] with Clough–Penzien high-pass filtering [8]'),
        ('Jennings-type envelope', 'Jennings-type envelope [9]'),
        ('(Boore 2003 stochastic method)', '(stochastic method [10])'),
        ('[Eqs. 10–11]', '(Eqs. 10–11 of [1])'), ('[Eq. 12]', '(Eq. 12 of [1])'), ('[Eq. 13]', '(Eq. 13 of [1])')]
REFS = [
    'Fu, C., Wang, L., Wang, Z., Xue, S., Xie, L. (2025). Rotating semi-active tuned liquid column damper for bi-directional eccentric structural seismic response control. Journal of Building Engineering, 103, 112205. https://doi.org/10.1016/j.jobe.2025.112205.',
    'Wang, Z., Ubertini, F., Laflamme, S. (2022). Ensemble of long short-term memory recurrent neural network for semi-active control of tuned liquid wall damper. Engineering Structures, 270, 114771. https://doi.org/10.1016/j.engstruct.2022.114771.',
    'Kim, H.S., Kim, U. (2023). Development of a control algorithm for a semi-active mid-story isolation system using reinforcement learning. Applied Sciences, 13(4), 2053. https://doi.org/10.3390/app13042053.',
    'AlHamaydeh, M., Tellab, S., Tariq, U. (2024). Deep-learning-based strong ground motion signal prediction in real time. Buildings, 14(5), 1267. https://doi.org/10.3390/buildings14051267.',
    'Farsijani, D., Gholam, S., Karampour, H., Talebian, N. (2025). Machine-learning based performance assessment of TMD-equipped buildings subjected to near-field pulse-like ground motions. Journal of Building Engineering, 105, 112380. https://doi.org/10.1016/j.jobe.2025.112380.',
    'Kanai, K. (1957). Semi-empirical formula for the seismic characteristics of the ground. Bulletin of the Earthquake Research Institute, University of Tokyo, 35, 309-325.',
    'Tajimi, H. (1960). A statistical method of determining the maximum response of a building structure during an earthquake. Proceedings of the 2nd World Conference on Earthquake Engineering, Tokyo, Japan, July.',
    'Clough, R.W., Penzien, J. (2003). Dynamics of structures (3rd ed.). Computers and Structures, Berkeley, CA, USA.',
    'Jennings, P.C., Housner, G.W., Tsai, N.C. (1968). Simulated earthquake motions. Report, Earthquake Engineering Research Laboratory, California Institute of Technology, Pasadena, CA, USA.',
    'Boore, D.M. (2003). Simulation of ground motion using the stochastic method. Pure and Applied Geophysics, 160(3), 635-676. https://doi.org/10.1007/PL00012553.',
]
TNR, ARIAL, BLUE = 'Times New Roman', 'Arial', RGBColor(0, 0, 0xFF)
TEXT_W = 15.4   # cm (A4 21.0 − 2 × 2.8)


# ── 원고 읽기 ──
md = open(SRC, encoding='utf-8').read()
md = md[:md.index('\n# References')]
for a, b in CITE:
    assert a in md, a
    md = md.replace(a, b)
abstract = re.search(r'# Abstract\n\n(.+?)\n', md).group(1)
body = md[md.index('# 1. Introduction'):]

# ── 식: pandoc으로 OMML 만들기 ──
eqs = re.findall(r'\$\$\n(.+?)\n\$\$', body, re.S)
eq_tex, eq_no = [], []
for e in eqs:
    m = re.search(r'\\qquad \((\d+)\)\s*$', e.strip())
    eq_no.append(m.group(1)); eq_tex.append(e.strip()[:m.start()].strip().rstrip(','))
tmp = os.path.join(tempfile.gettempdir(), 'tp_eq.docx')
pypandoc.convert_text('\n\n'.join(f'$${t}$$' for t in eq_tex), 'docx', format='markdown', outputfile=tmp)
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
ex = etree.fromstring(zipfile.ZipFile(tmp).read('word/document.xml'))
omath = [p.find(f'{{{M}}}oMath') for p in ex.iter(f'{{{M}}}oMathPara')]
assert len(omath) == len(eq_tex), (len(omath), len(eq_tex))

# ── 양식 열기, 표지 채우기 ──
d = docx.Document(TPL)
P = d.paragraphs

def only(p, keep):            # 문단에서 keep개 run만 남김
    for r in p.runs[keep:]:
        r._r.getparent().remove(r._r)

def drop(p):
    p._p.getparent().remove(p._p)

P[4].runs[0].text = TITLE; only(P[4], 1); drop(P[5])

ap = P[7]; runs = ap.runs
fn_run = copy.deepcopy(runs[2]._r); txt_r = copy.deepcopy(runs[0]._r); sup_r = copy.deepcopy(runs[3]._r)
for r in list(ap.runs):
    r._r.getparent().remove(r._r)
for a in ap._p.findall(qn('w:proofErr')) + ap._p.findall(qn('w:bookmarkStart')) + ap._p.findall(qn('w:bookmarkEnd')):
    ap._p.remove(a)
def add(tmpl, text):
    r = copy.deepcopy(tmpl)
    for t in r.findall(qn('w:t')): r.remove(t)
    t = OxmlElement('w:t'); t.set(qn('xml:space'), 'preserve'); t.text = text; r.append(t); ap._p.append(r)
add(txt_r, 'Jungju Park'); add(sup_r, '1a'); add(txt_r, ', Yun Sik Choi'); add(sup_r, '1a')
add(txt_r, ' and Jae-Hoon Jeong'); ap._p.append(fn_run); add(sup_r, '1')

P[9].runs[1].text = AFFIL; only(P[9], 2); drop(P[10]); drop(P[11])
P[15].runs[3].text = abstract; only(P[15], 4)
P[15].runs[3].font.name = TNR; P[15].runs[3].font.size = Pt(10.5); P[15].runs[3].bold = False
P[17].runs[2].text = ' ' + KEYWORDS; only(P[17], 3)

# 머리말 (홀수: 제목, 짝수: 저자, 첫 쪽: 학술지)
def set_header(hdr, old, new):
    for p in hdr.paragraphs:
        if old in p.text:
            p.runs[0].text = new; only(p, 1); return
    raise KeyError(old)
sec = d.sections[0]
set_header(sec.header, 'Title of the manuscript', TITLE)
set_header(sec.even_page_header, 'First and middle name initials', RUN_AUTH)
for p in sec.first_page_header.paragraphs:
    for r in p.runs:
        if r.text == 'cac': r.text = 'sss'

# 각주: * 교신저자, a 공동 1저자, b 삭제
fpart = [p for p in d.part.package.parts if p.partname == '/word/footnotes.xml'][0]
fx = etree.fromstring(fpart.blob); W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
fn1 = [f for f in fx.findall(f'{{{W}}}footnote') if f.get(f'{{{W}}}id') == '1'][0]
paras = fn1.findall(f'{{{W}}}p')
def ptext(p): return ''.join(t.text or '' for t in p.iter(f'{{{W}}}t'))
def reset(p, keep_first, text):
    rs = p.findall(f'{{{W}}}r'); base = rs[min(1, len(rs) - 1)]
    for r in rs[keep_first:]: p.remove(r)
    for h in p.findall(f'{{{W}}}hyperlink'): p.remove(h)    # 템플릿 email@domain.com 자리
    r = copy.deepcopy(base)
    for c in list(r):
        if c.tag != f'{{{W}}}rPr': r.remove(c)
    va = r.find(f'{{{W}}}rPr/{{{W}}}vertAlign')
    if va is not None: va.getparent().remove(va)
    t = etree.SubElement(r, f'{{{W}}}t'); t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve'); t.text = text; p.append(r)
for p in paras:
    s = ptext(p)
    if s.startswith('Corresponding'):
        reset(p, 1, CORR)
    elif s.startswith('a'):
        reset(p, 1, EQUAL)
    elif s.startswith('b'):
        fn1.remove(p)
fpart._blob = etree.tostring(fx, xml_declaration=True, encoding='UTF-8', standalone=True)

# 템플릿 본문(예시) 삭제: Keywords 다음 빈 줄 두 개 이후 ~ sectPr 앞
bd = d.element.body; kw = P[17]._p
kids = list(bd); start = kids.index(kw) + 3
for el in kids[start:]:
    if el.tag != qn('w:sectPr'): bd.remove(el)

# ── 본문 쓰기 ──
def fonts(r, name=TNR, size=11, bold=None, italic=None, color=None):
    r.font.name = name; r.font.size = Pt(size)
    rpr = r._r.get_or_add_rPr(); rf = rpr.find(qn('w:rFonts'))
    if rf is None: rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
    rf.set(qn('w:eastAsia'), name)
    if bold is not None: r.bold = bold
    if italic is not None: r.italic = italic
    if color is not None: r.font.color.rgb = color
    return r

NUMREF = re.compile(r'(\[)(\d+(?:[,–-] ?\d+)*)(\])|((?:Figs?\.|Figure|Eqs?\.) \(?)(\d+)')
def emit(p, text, size=11, name=TNR, bold=False, italic=False, refs=True):
    """인라인: **굵게**, *기울임*, x_sub 아래첨자, [n] · Fig. n · Eq. (n) 숫자 파란색."""
    for piece in re.split(r'(\*\*.+?\*\*|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))', text):
        if not piece: continue
        b, i = bold, italic
        if piece.startswith('**') and piece.endswith('**'): piece, b = piece[2:-2], True
        elif piece.startswith('*') and piece.endswith('*') and len(piece) > 2: piece, i = piece[1:-1], True
        for k, part in enumerate(re.split(r'(?<!\s)_([A-Za-z0-9θ]+(?:,[A-Za-z]+)?)', piece)):
            if not part: continue
            if k % 2:
                r = fonts(p.add_run(part), name, size, b, i); r.font.subscript = True; continue
            pos = 0
            for m in (NUMREF.finditer(part) if refs else []):
                if m.start() > pos: fonts(p.add_run(part[pos:m.start()]), name, size, b, i)
                if m.group(1):
                    fonts(p.add_run('['), name, size, b, i); fonts(p.add_run(m.group(2)), name, size, b, i, BLUE); fonts(p.add_run(']'), name, size, b, i)
                else:
                    fonts(p.add_run(m.group(4)), name, size, b, i); fonts(p.add_run(m.group(5)), name, size, b, i, BLUE)
                pos = m.end()
            if pos < len(part): fonts(p.add_run(part[pos:]), name, size, b, i)

def para(text='', indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=11, name=TNR, **kw):
    p = d.add_paragraph(); pf = p.paragraph_format; pf.alignment = align
    pf.space_before = pf.space_after = Pt(0)
    if indent: pf.first_line_indent = Cm(0.5)
    if text: emit(p, text, size, name, **kw)
    else: fonts(p.add_run(''), name, size)
    return p

def blank(n=1):
    for _ in range(n): para(indent=False)

def table(rows, caption):
    c = para(caption, indent=False, size=10, refs=False); c.paragraph_format.space_after = Pt(2.4); c.paragraph_format.keep_with_next = True
    nc = len(rows[0]); t = d.add_table(rows=len(rows), cols=nc)
    pr = t._tbl.tblPr; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tw = pr.find(qn('w:tblW'))
    tw.set(qn('w:w'), '5000'); tw.set(qn('w:type'), 'pct')
    bdr = OxmlElement('w:tblBorders')
    for side, val in (('top', 'double'), ('bottom', 'single')):
        e = OxmlElement(f'w:{side}'); e.set(qn('w:val'), val); e.set(qn('w:sz'), '4'); e.set(qn('w:space'), '0'); e.set(qn('w:color'), 'auto'); bdr.append(e)
    nxt = [c for c in pr if c.tag in (qn('w:shd'), qn('w:tblLayout'), qn('w:tblCellMar'), qn('w:tblLook'))]
    (nxt[0].addprevious(bdr) if nxt else pr.append(bdr))
    lens = [max(len(re.sub(r'\*', '', r[j])) for r in rows) for j in range(nc)]
    ws = [max(1.6, TEXT_W * l / sum(lens)) for l in lens]; ws = [w * TEXT_W / sum(ws) for w in ws]
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = t.cell(i, j); cell.width = Cm(ws[j])
            if i == 0:
                tcb = OxmlElement('w:tcBorders'); e = OxmlElement('w:bottom')
                e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '4'); e.set(qn('w:space'), '0'); e.set(qn('w:color'), 'auto')
                tcb.append(e); cell._tc.get_or_add_tcPr().append(tcb)
            p = cell.paragraphs[0]; p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            emit(p, v.strip(), 10)
    blank()

def figure(path, caption):
    p = para(indent=False, align=WD_ALIGN_PARAGRAPH.CENTER); p.paragraph_format.keep_with_next = True
    p.runs[0].add_picture(path, width=Cm(14.5))
    para(caption, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, size=10, refs=False)
    blank()

def equation(k):
    p = d.add_paragraph(); pf = p.paragraph_format; pf.space_before = pf.space_after = Pt(3)
    pf.tab_stops.add_tab_stop(Cm(TEXT_W / 2), WD_TAB_ALIGNMENT.CENTER); pf.tab_stops.add_tab_stop(Cm(TEXT_W), WD_TAB_ALIGNMENT.RIGHT)
    fonts(p.add_run('\t'))
    p._p.append(copy.deepcopy(omath[k]))
    fonts(p.add_run(f'\t({eq_no[k]})'))

lines = body.split('\n'); i = 0; k_eq = 0; after_eq = False
while i < len(lines):
    ln = lines[i]
    if not ln.strip():
        i += 1; continue
    if ln.startswith('# '):
        blank(2 if i else 0); p = para(ln[2:], indent=False, name=ARIAL, bold=True); p.paragraph_format.keep_with_next = True; blank()
        i += 1; continue
    if ln.startswith('## '):
        blank(); p = para(ln[3:], name=ARIAL); p.paragraph_format.keep_with_next = True; blank()
        i += 1; continue
    if ln.startswith('$$'):
        equation(k_eq); k_eq += 1; i += 1
        while not lines[i].startswith('$$'): i += 1
        i += 1; after_eq = True; continue
    m = re.match(r'!\[\*\*Fig\. (\d+)\.\*\* (.+)\]\((.+?)\)', ln)
    if m:
        figure(m.group(3), f'Figure {m.group(1)}. {m.group(2)}'); i += 1; continue
    m = re.match(r'\*\*Table (\d+)\.\*\* (.+)', ln)
    if m and any(l.startswith('|') for l in lines[i + 1:i + 3]):
        cap = f'Table {m.group(1)}. {m.group(2)}'; i += 1
        while not lines[i].startswith('|'): i += 1
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            if not re.match(r'^\|[-| :]+\|$', lines[i]): rows.append([c for c in lines[i].strip().strip('|').split('|')])
            i += 1
        table(rows, cap); continue
    if ln.startswith('|'):                     # 캡션 없는 표 (4.1 전략표 등은 캡션 있음)
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            if not re.match(r'^\|[-| :]+\|$', lines[i]): rows.append(lines[i].strip().strip('|').split('|'))
            i += 1
        table(rows, ''); continue
    m = re.match(r'(- |\d+\. )(.+)', ln)
    if m:
        mark = '•' if m.group(1) == '- ' else m.group(1).strip()
        p = para(f'{mark}\t{m.group(2)}', indent=False); pf = p.paragraph_format
        pf.left_indent = Cm(0.9); pf.first_line_indent = Cm(-0.5); pf.tab_stops.add_tab_stop(Cm(0.9))
        i += 1; continue
    para(ln, indent=not (after_eq and re.match(r'(where|so that|and |and enters|so the|which|so)\b', ln)))
    after_eq = False; i += 1

# 참고문헌 (번호 목록: 템플릿의 numId 48 그대로)
blank(2); para('References', indent=False, name=ARIAL, bold=True); blank()
for ref in REFS:
    p = para(indent=False, size=10); p.runs[0].text = ref
    pPr = p._p.get_or_add_pPr(); num = OxmlElement('w:numPr')
    for tag, v in (('w:ilvl', '0'), ('w:numId', '48')):
        e = OxmlElement(tag); e.set(qn('w:val'), v); num.append(e)
    pPr.insert(0, num); pf = p.paragraph_format; pf.left_indent = Cm(0.63); pf.first_line_indent = Cm(-0.63)

d.core_properties.title = TITLE; d.core_properties.author = 'Jungju Park, Yun Sik Choi, Jae-Hoon Jeong'
d.save(OUT)
print('ok', OUT, '| eqs', k_eq, '| refs', len(REFS))
