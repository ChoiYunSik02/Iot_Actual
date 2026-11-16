# -*- coding: utf-8 -*-
"""MATLAB에서 호출하는 추론 모듈 (forecast_torch.m).

load(path)  : <path>.pt 와 <path>.json을 읽어 모델을 메모리에 둔다 (한 번)
infer(x)    : x = 길이 1500 (MATLAB 3x500 배열을 열 우선으로 편 것: [c1 c2 c3]를 시간마다) → 길이 800 (정규화)
MATLAB 쪽에서 numpy 변환·호출·역변환 시간을 함께 잰다(예측 계산 지연에 포함).
"""
import json
import numpy as np
import torch
from pc_lstm import Forecaster

_M = {}


def load(path, threads=1):
    torch.set_num_threads(int(threads))
    with open(path + '.json', encoding='utf-8') as f:
        meta = json.load(f)
    m = Forecaster()
    m.load_state_dict(torch.load(path + '.pt', map_location='cpu'))
    m.eval()
    _M[path] = m
    return meta['val_mse']


def infer(path, x):
    m = _M[path]
    a = np.asarray(x, dtype=np.float32).reshape(500, 3)      # MATLAB 3x500 열 우선 → (T, C)
    with torch.no_grad():
        y = m(torch.from_numpy(a)[None])[0].numpy()
    return y.astype(np.float64)
