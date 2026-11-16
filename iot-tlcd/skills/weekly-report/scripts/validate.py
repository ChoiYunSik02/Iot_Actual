# -*- coding: utf-8 -*-
"""
생성한 보고서 PPT를 검증합니다.

  python validate.py "<파일경로.ppt>" [목표분]

점검 항목
  1. 슬라이드 밖으로 나간 도형 (표지 장식 원은 예외)
  2. 텍스트 상자 세로 넘침
  3. 표 셀 가로 넘침
  4. 발표자 노트 기준 예상 발표 시간

Windows: PYTHONIOENCODING=utf-8 을 붙여 실행하세요.
"""
import sys
import re
import math
import unicodedata
from pptx import Presentation

# 한국어 발표 낭독 속도 (자/분). 차분한 발표 기준.
CHARS_PER_MIN = 280


def _is_ellipse(sh):
    """도형이 원/타원인지 preset geometry로 판정합니다."""
    try:
        el = sh._element.spPr.find(
            '{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom')
        return el is not None and el.get('prst') == 'ellipse'
    except Exception:
        return False


def _w(ch):
    """문자 폭을 em 단위로 근사. 한글/전각 1.0, 영문 소문자 0.52."""
    if unicodedata.east_asian_width(ch) in 'WF':
        return 1.0
    if ch.isupper():
        return 0.62
    if ch == ' ':
        return 0.28
    return 0.52


def main(path, target_min=None):
    prs = Presentation(path)
    W, H = prs.slide_width, prs.slide_height
    geo = txt = cell = 0

    for i, s in enumerate(prs.slides, 1):
        for sh in s.shapes:
            if sh.left is None or sh.width is None:
                continue
            # 표지 장식 원(ellipse)은 의도적으로 화면 밖으로 나갑니다.
            # shape_type은 AUTO_SHAPE로만 나오므로 preset geometry를 직접 봅니다.
            if _is_ellipse(sh):
                continue
            if sh.top + sh.height > H + 9144:
                print('  [도형] s%d 아래로 벗어남 %.2fin' % (i, (sh.top + sh.height) / 914400))
                geo += 1
            if sh.left + sh.width > W + 9144:
                print('  [도형] s%d 오른쪽으로 벗어남 %.2fin' % (i, (sh.left + sh.width) / 914400))
                geo += 1

        for sh in s.shapes:
            if not sh.has_text_frame or not sh.text_frame.text.strip() or sh.width is None:
                continue
            bw, bh = sh.width / 914400.0, sh.height / 914400.0
            need = 0
            for para in sh.text_frame.paragraphs:
                t = ''.join(r.text for r in para.runs)
                if not t:
                    continue
                sz = max([r.font.size.pt for r in para.runs if r.font.size] or [11])
                ls = para.line_spacing or 1.2
                lines = max(1, math.ceil(sum(_w(c) for c in t) * sz / 72.0 / bw)) if bw > 0 else 1
                need += lines * (sz / 72.0) * ls
            # 허용치 1.4는 카드 밖으로 0.1인치 삐져나가는 경우를 놓쳤습니다.
            # 박스 높이는 의도적으로 정하므로 1.15로 조입니다.
            if need > bh * 1.15:
                print('  [텍스트] s%d 높이 %.2f < 필요 %.2f :: %s'
                      % (i, bh, need, sh.text_frame.text[:40].replace('\n', ' ')))
                txt += 1

        for sh in s.shapes:
            if not sh.has_table:
                continue
            t = sh.table
            for ri in range(len(t.rows)):
                for ci in range(len(t.columns)):
                    cw = t.columns[ci].width / 914400.0 - 0.22
                    body = t.cell(ri, ci).text
                    if not body:
                        continue
                    szs = [r.font.size.pt for p in t.cell(ri, ci).text_frame.paragraphs
                           for r in p.runs if r.font.size]
                    sz = max(szs or [10.5])
                    # 셀 안의 줄바꿈은 실제로 줄이 나뉘므로 가장 긴 줄만 봅니다
                    need = max(sum(_w(c) for c in line) for line in body.split('\n')) * sz / 72.0
                    if need > cw * 1.03:
                        print('  [표] s%d r%dc%d 폭 %.2f < 필요 %.2f :: %s'
                              % (i, ri, ci, cw, need, body[:35]))
                        cell += 1

    print()
    print('슬라이드 %d장 | 도형 %d건 | 텍스트 넘침 %d건 | 표 셀 넘침 %d건'
          % (len(prs.slides), geo, txt, cell))

    total = 0.0
    have_notes = 0
    print()
    for i, s in enumerate(prs.slides, 1):
        n = s.notes_slide.notes_text_frame.text
        if n.strip():
            have_notes += 1
        body = re.sub(r'\[\d+:\d+\]', '', n).split('--- 예상 질문')[0]
        ch = len(re.sub(r'\s', '', body))
        sec = ch / (CHARS_PER_MIN / 60.0)
        total += sec
        m = re.search(r'\[(\d+):(\d+)\]', n)
        plan = int(m.group(1)) * 60 + int(m.group(2)) if m else 0
        print('  s%2d  계획 %d:%02d   추정 %d:%02d   (%d자)'
              % (i, plan // 60, plan % 60, int(sec) // 60, int(sec) % 60, ch))

    print()
    print('발표자 노트 %d/%d장 | 예상 발표 시간 %d분 %d초 (기준 %d자/분)'
          % (have_notes, len(prs.slides), int(total) // 60, int(total) % 60, CHARS_PER_MIN))

    if target_min:
        tgt = float(target_min) * 60
        pct = total / tgt * 100
        print('목표 %g분 대비 %.0f%%' % (float(target_min), pct))
        if pct > 100:
            print('  → 초과입니다. 대본을 줄이거나 슬라이드를 통합하세요.')
        elif pct < 80:
            print('  → 여유가 많습니다. 내용을 더 넣을 수 있습니다.')
        else:
            print('  → 적정 범위입니다.')

    return geo + txt + cell


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(1 if main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None) else 0)
