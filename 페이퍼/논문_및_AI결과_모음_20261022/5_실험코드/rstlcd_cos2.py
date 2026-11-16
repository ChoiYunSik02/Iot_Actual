# -*- coding: utf-8 -*-
"""rstlcd.py와 같은 모델이되 원문 식 (20) 그대로: 강성에 cosθ가 한 번 더 곱해짐 (cos_twice=True가 기본).
2026-10-22 점검: PEER 8쌍 RS − 수동 = 기존(cos 한 번) −0.25%p → 원문식 +0.56%p. 원문 PDF 9쪽 식 (16)(17)(20) 대조.
"""
from rstlcd import *          # noqa: F401,F403  (상수 · Device · metrics · reduction 등 그대로)
import rstlcd as _base

def simulate(*args, **kwargs):
    kwargs.setdefault('cos_twice', True)
    return _base.simulate(*args, **kwargs)
