# -*- coding: utf-8 -*-
"""
IOT 액추에이터 팀 주간보고서 빌더.

1주차 발표자료에서 추출한 디자인 시스템을 그대로 재현합니다.
색상·좌표·폰트는 references/design-tokens.md 참조.

사용 예
-------
    import sys; sys.path.insert(0, '<scripts 경로>')
    from deck import *

    prs = new_deck()

    s = dark()
    head(s, 'CONTENTS', '목차', dark=True)
    pg(s, 2); notes(s, '[0:20] …')

    s = light()
    head(s, 'BACKGROUND', '주제 변경 배경')
    bullets(s, ['첫째 …', '둘째 …'])
    bar(s, '핵심', '한 줄 결론', sub='보조 설명')
    pg(s, 3); notes(s, '[1:00] …')

    save(prs, r'C:\\...\\보고서_3주차')

요구사항: pip install python-pptx
Windows 실행 시 PYTHONIOENCODING=utf-8 권장.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

__all__ = ['C', 'new_deck', 'light', 'dark', 'T', 'rr', 'rect', 'circ', 'arrow',
           'numdot', 'head', 'pg', 'bullets', 'bar', 'table', 'cards', 'notes',
           'img', 'movie', 'save', 'DARK']

C = dict(dark='0C343D', dark2='1A2E32', mid='134450', mint='00C3B1', coral='CC4125',
         white='FFFFFF', body='262626', panelline='E0E6E6', minttx='8FE0D8',
         mintbg='E4F5F3', tealsub='D8E4E2', muted='B9CFCD', muted2='8FB3B0',
         grid='E8DEDC', altrow='F3EDEC', lightbg='F3F3F3', f5='F5F5F5',
         warnlbl='FFE8B8', warnbg='FFF0DC', softcoral='FBEAE7', coralpale='F5B7A8')

CARD_W = {2: (5.9, 6.2), 3: (3.85, 4.13), 4: (2.85, 3.09), 5: (2.25, 2.47)}

_PRS = None
DARK = set()          # 어두운 배경 슬라이드 번호 (페이지 번호 색 결정용)


def new_deck():
    """새 프레젠테이션 생성. 이후 light()/dark()가 여기에 슬라이드를 추가합니다."""
    global _PRS
    _PRS = Presentation()
    _PRS.slide_width = Emu(12188952)
    _PRS.slide_height = Emu(6858000)
    DARK.clear()
    return _PRS


def _add(bg):
    s = _PRS.slides.add_slide(_PRS.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = RGBColor.from_string(bg)
    return s


def light():
    """밝은 배경(F3F3F3) 슬라이드 추가."""
    return _add(C['lightbg'])


def dark():
    """어두운 배경(0C343D) 슬라이드 추가. pg() 색 보정을 위해 DARK.add(번호) 필요."""
    return _add(C['dark'])


def T(s, x, y, w, h, text, size, color, bold=False, align='l',
      spc=None, ls=None, anchor='t'):
    """텍스트 상자. text의 '\\n'은 문단으로 분리됩니다. 좌표 단위는 인치."""
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {'t': MSO_ANCHOR.TOP, 'c': MSO_ANCHOR.MIDDLE,
                          'b': MSO_ANCHOR.BOTTOM}[anchor]
    for i, line in enumerate(text.split('\n')):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}[align]
        p.line_spacing = ls or 1.2
        r = p.add_run()
        r.text = line
        r.font.name = 'Arial'
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = RGBColor.from_string(color)
        if spc:
            r._r.get_or_add_rPr().set('spc', str(spc))
    return tf


def rr(s, x, y, w, h, fill, line=None, adj=0.06):
    """둥근 사각형 패널."""
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = adj
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(fill)
    if line:
        shp.line.color.rgb = RGBColor.from_string(line)
        shp.line.width = Pt(0.75)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def rect(s, x, y, w, h, fill):
    """직사각형. 얇은 구분선(h=0.012)으로도 씁니다."""
    shp = s.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                             Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(fill)
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def circ(s, x, y, d, fill):
    """원. 표지 장식이나 번호 배경에 사용."""
    shp = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(fill)
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def arrow(s, x, y, w, h, fill):
    """셰브론 화살표. 흐름도 연결에 사용."""
    shp = s.shapes.add_shape(MSO_SHAPE.CHEVRON, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(fill)
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def numdot(s, x, y, n, fill=None, d=0.4, size=11):
    """원형 번호 배지."""
    circ(s, x, y, d, fill or C['mint'])
    T(s, x, y, d, d, str(n), size, C['white'], True, 'c', anchor='c')


def head(s, eyebrow, title, dark=False):
    """상단 eyebrow + 제목. 모든 내용 슬라이드에 필수."""
    T(s, 0.6, 0.42, 9.0, 0.35, eyebrow, 12,
      C['mint'] if dark else C['coral'], True, spc=200)
    T(s, 0.6, 0.72, 12.1, 0.8, title, 28,
      C['white'] if dark else C['dark'], True, ls=1.1)


def pg(s, n):
    """우하단 페이지 번호. 어두운 슬라이드는 DARK.add(n)을 먼저 호출하세요."""
    T(s, 12.05, 7.08, 1.1, 0.3, '%02d' % n, 10,
      C['muted'] if n in DARK else C['body'], align='r')


def bullets(s, items, y=2.44, tw=6.05, gap=0.72, x=0.6, dotcol=None,
            size=11.5, txt=None):
    """번호 배지가 붙은 항목 목록."""
    for i, t in enumerate(items):
        yy = y + i * gap
        numdot(s, x, yy + 0.05, i + 1, dotcol)
        T(s, x + 0.55, yy, tw, gap - 0.07, t, size, txt or C['dark2'], ls=1.25)


def bar(s, label, text, y=5.65, h=1.55, sub=None):
    """하단 결론 바. 슬라이드마다 한 줄 결론을 담습니다."""
    rr(s, 0.6, y, 12.1, h, C['dark'], C['panelline'])
    T(s, 0.9, y + 0.15, 11.5, 0.3, label, 11, C['minttx'], True, spc=150)
    T(s, 0.9, y + 0.5, 11.5, 0.45, text, 12.5, C['white'], True, ls=1.2)
    if sub:
        T(s, 0.9, y + 0.98, 11.5, 0.55, sub, 11, C['tealsub'], ls=1.25)


def cards(s, items, y, h, on_dark=False):
    """
    균등 분할 카드. items = [(제목, 본문, 색), ...] — 2~5개 지원.
    폭과 간격은 디자인 규격에서 자동 결정됩니다.
    """
    n = len(items)
    if n not in CARD_W:
        raise ValueError('카드는 2~5개만 지원합니다 (요청: %d)' % n)
    w, step = CARD_W[n]
    for i, (title, body, col) in enumerate(items):
        x = 0.6 + i * step
        rr(s, x, y, w, h, col, C['panelline'])
        T(s, x + 0.22, y + 0.2, w - 0.44, 0.3, title, 12.5, C['white'], True)
        T(s, x + 0.22, y + 0.6, w - 0.44, h - 0.8, body, 10.5, C['f5'], ls=1.3)


def _style_table(tbl, nrows, ncols, hdr=None):
    for ri in range(nrows):
        for ci in range(ncols):
            cell = tbl.cell(ri, ci)
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor.from_string(
                (hdr or C['dark']) if ri == 0
                else (C['altrow'] if ri % 2 == 0 else C['white']))
            tcPr = cell._tc.get_or_add_tcPr()
            for tag in ('a:lnL', 'a:lnR', 'a:lnT', 'a:lnB'):
                ln = tcPr.makeelement(qn(tag), {'w': '9525', 'cap': 'flat',
                                                'cmpd': 'sng', 'algn': 'ctr'})
                sf = ln.makeelement(qn('a:solidFill'), {})
                sf.append(sf.makeelement(qn('a:srgbClr'), {'val': C['grid']}))
                ln.append(sf)
                tcPr.append(ln)


def table(s, rows, x, y, w, h, widths, size=10.5, hdr=None):
    """
    표. rows[0]이 헤더행입니다. widths 합은 w와 같아야 합니다.
    1열과 헤더는 자동으로 Bold 처리됩니다.
    """
    if abs(sum(widths) - w) > 0.05:
        raise ValueError('열 너비 합(%.2f)이 표 너비(%.2f)와 다릅니다' % (sum(widths), w))
    gt = s.shapes.add_table(len(rows), len(rows[0]),
                            Inches(x), Inches(y), Inches(w), Inches(h)).table
    for i, cw in enumerate(widths):
        gt.columns[i].width = Inches(cw)
    for r in gt.rows:
        r.height = Inches(h / len(rows))
    _style_table(gt, len(rows), len(rows[0]), hdr)
    for ri, row in enumerate(rows):
        for ci, v in enumerate(row):
            cell = gt.cell(ri, ci)
            cell.text_frame.word_wrap = True
            p = cell.text_frame.paragraphs[0]
            p.line_spacing = 1.1
            r = p.add_run()
            r.text = v
            r.font.name = 'Arial'
            r.font.size = Pt(size)
            r.font.bold = (ri == 0 or ci == 0)
            r.font.color.rgb = RGBColor.from_string(
                C['white'] if ri == 0 else (C['dark'] if ci == 0 else C['dark2']))
    return gt


def img(s, path, x, y, w=None, h=None, frame=None):
    """
    이미지 삽입. w 또는 h 중 하나만 주면 원본 비율을 유지합니다.
    frame에 색을 주면 이미지 뒤에 테두리 패널을 깔아 슬라이드에 녹아들게 합니다.

    MATLAB 그래프처럼 흰 배경 이미지는 밝은 슬라이드에 그냥 얹으면 자연스럽고,
    어두운 슬라이드에서는 frame=C['white'] 로 여백을 주는 편이 낫습니다.
    """
    if w is None and h is None:
        raise ValueError('w 또는 h 중 하나는 지정해야 합니다')
    kw = {}
    if w is not None:
        kw['width'] = Inches(w)
    if h is not None:
        kw['height'] = Inches(h)
    pic = s.shapes.add_picture(path, Inches(x), Inches(y), **kw)
    if frame:
        pad = 0.12
        bg = rr(s, x - pad, y - pad,
                pic.width / 914400.0 + 2 * pad,
                pic.height / 914400.0 + 2 * pad, frame, adj=0.03)
        # 패널을 이미지 뒤로 보냅니다
        sp = bg._element
        sp.getparent().remove(sp)
        s.shapes._spTree.insert(2, sp)
    return pic


def movie(s, path, x, y, w, h, poster=None):
    """
    동영상 삽입. 발표 중 클릭하면 재생됩니다.
    poster에 PNG 경로를 주면 정지 상태에서 그 이미지가 보입니다 (권장).
    파일이 PPTX 안에 포함되므로 용량이 커집니다.
    """
    return s.shapes.add_movie(path, Inches(x), Inches(y), Inches(w), Inches(h),
                              poster_frame_image=poster, mime_type='video/mp4')


def notes(s, text):
    """발표자 노트. 맨 앞에 '[분:초]' 형식으로 배정 시간을 적으면 검증기가 읽습니다."""
    s.notes_slide.notes_text_frame.text = text


def save(prs, base_path):
    """
    .ppt와 .pptx를 함께 저장합니다.
    PowerPoint에서 파일이 열려 있으면 _v2 이름으로 회피하고 그 사실을 알립니다.
    base_path에는 확장자를 빼고 넘기세요.
    """
    saved, locked = [], []
    for ext in ('.ppt', '.pptx'):
        for suffix in ('', '_v2'):
            try:
                prs.save(base_path + suffix + ext)
                saved.append(base_path + suffix + ext)
                break
            except PermissionError:
                locked.append(base_path + suffix + ext)
    if locked:
        print('잠김(PowerPoint에서 닫아주세요):')
        for f in locked:
            print('  -', f)
    for f in saved:
        print('저장됨:', f)
    return saved
