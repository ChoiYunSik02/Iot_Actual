# -*- coding: utf-8 -*-
"""입력 지진 불러오기.

- 원문 표 2의 15쌍: PEER NGA-West2 .AT2 파일을 `페이퍼/입력/PEER/`에 넣으면 파일 이름의 성분 코드로 자동으로 찾음
- 보유 기록 3쌍: `6주차 발표/.../보유기록_데이터/` (El Centro 1940, 포항 2017 BUS2, 경주 2016 CHJ2)
모든 기록은 반환 전에 각 성분의 최대 가속도를 35 cm/s²로 맞춤 (원문 3.2절, 처리: 성분별 정규화).
"""
import glob, os, re
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PEER_DIR = os.path.join(ROOT, '페이퍼', '입력', 'PEER')
HELD_DIR = os.path.join(ROOT, '6주차 발표', '6주차_피드백반영_정리', '시뮬레이션_테스트', '보유기록_데이터')
PGA_TARGET = 0.35   # m/s² (35 cm/s²)

# 원문 표 2: (번호, 관측소, X 성분, Y 성분)
PAPER_PAIRS = [
    (1, 'El Centro Array #11', 'IMPVALL-E11140', 'IMPVALL-E11230'),
    (2, 'Aeropuerto Mexicali', 'IMPVALL-AEP045', 'IMPVALL-AEP315'),
    (3, 'El Centro Differential Array', 'IMPVALL-EDA270', 'IMPVALL-EDA360'),
    (4, 'Brawley Airport', 'IMPVALL-BRA225', 'IMPVALL-BRA315'),
    (5, 'EC County Center FF', 'IMPVALL-ECC002', 'IMPVALL-ECC092'),
    (6, 'El Centro Array #10', 'IMPVALL-E10050', 'IMPVALL-E10320'),
    (7, 'Agrarias', 'IMPVALL-AGR003', 'IMPVALL-AGR273'),
    (8, 'El Centro Array #5', 'IMPVALL-E05140', 'IMPVALL-E05230'),
    (9, 'El Centro Array #7', 'IMPVALL-E07140', 'IMPVALL-E07230'),
    (10, 'El Centro Array #8', 'IMPVALL-E08140', 'IMPVALL-E08230'),
    (11, 'El Centro Array #3', 'IMPVALL-E03140', 'IMPVALL-E03230'),
    (12, 'Holtville Post Office', 'IMPVALL-HVP225', 'IMPVALL-HVP315'),
    (13, 'Pacoima Dam', 'NORTHR-PAC175', 'NORTHR-PAC265'),
    (14, 'KJMA', 'KOBE-KJM000', 'KOBE-KJM090'),
    (15, 'CHY006', 'CHICHI-CHY006-N', 'CHICHI-CHY006-W'),
]

HELD_PAIRS = [
    ('El Centro 1940', 'elcentro_NS.txt', 'elcentro_EW.txt', 'g'),
    ('포항 2017 BUS2', 'pohang_BUS2_BHE.txt', 'pohang_BUS2_BHN.txt', 'm/s2'),
    ('경주 2016 CHJ2', 'gyeongju_CHJ2_BHE.txt', 'gyeongju_CHJ2_BHN.txt', 'm/s2'),
]


def _key(s):
    return re.sub(r'[^A-Z0-9]', '', s.upper())


def read_at2(path):
    """PEER .AT2 → (dt [s], 가속도 [m/s²])."""
    with open(path, encoding='latin-1') as fh:
        lines = fh.readlines()
    for j, ln in enumerate(lines[:10]):
        m = re.search(r'NPTS\s*=\s*(\d+)\s*,\s*DT\s*=\s*([0-9.Ee+-]+)', ln)
        if m:
            npts, dt = int(m.group(1)), float(m.group(2)); break
        m = re.match(r'\s*(\d+)\s+([0-9.Ee+-]+)\s', ln)       # 옛 형식: "npts dt ..."
        if m and j >= 3:
            npts, dt = int(m.group(1)), float(m.group(2)); break
    else:
        raise ValueError('AT2 헤더를 못 읽음: ' + path)
    vals = np.array(' '.join(lines[j + 1:]).split(), float)[:npts]
    return dt, vals * 9.81


def find_peer(token):
    """'IMPVALL-E11140' → PEER_DIR 안에서 사건 코드와 성분 코드를 모두 포함하는 .AT2."""
    ev, comp = token.split('-', 1)
    hits = [p for p in glob.glob(os.path.join(PEER_DIR, '**', '*.AT2'), recursive=True)
            if _key(ev) in _key(os.path.basename(p)) and _key(comp) in _key(os.path.basename(p))]
    hits = [p for p in hits if not re.search(r'(UP|DWN|-V)\.AT2$', p, re.I)]
    return hits[0] if hits else None


def _resample(dt_in, x, dt):
    t_in = np.arange(len(x)) * dt_in
    t = np.arange(0, t_in[-1] + 1e-9, dt)
    return np.interp(t, t_in, x)


def _pair(xx, yy, dt_x, dt_y, dt, tail):
    x = _resample(dt_x, xx - xx.mean(), dt); y = _resample(dt_y, yy - yy.mean(), dt)
    n = max(len(x), len(y)) + int(tail / dt)
    x = np.r_[x, np.zeros(n - len(x))]; y = np.r_[y, np.zeros(n - len(y))]
    return x / np.abs(x).max() * PGA_TARGET, y / np.abs(y).max() * PGA_TARGET


def paper_pairs(dt=0.01, tail=10.0):
    """원문 15쌍 중 받아 둔 것만. 반환: [(번호, 관측소, agx, agy)], 없는 성분 목록."""
    out, missing = [], []
    for no, st, tx, ty in PAPER_PAIRS:
        px, py = find_peer(tx), find_peer(ty)
        if not (px and py):
            missing += [t for t, p in ((tx, px), (ty, py)) if not p]; continue
        (dx, x), (dy, y) = read_at2(px), read_at2(py)
        out.append((no, st) + _pair(x, y, dx, dy, dt, tail))
    return out, missing


def held_pairs(dt=0.01, tail=10.0, dur=60.0):
    out = []
    for name, fx, fy, unit in HELD_PAIRS:
        dx_, dy_ = (np.loadtxt(os.path.join(HELD_DIR, f), comments='#') for f in (fx, fy))
        sc = 9.81 if unit == 'g' else 1.0
        if unit != 'g':   # 한국 기록: P파 5 s 전부터 dur초 (보유기록 README 방식)
            t0 = dx_[np.argmax(np.abs(dx_[:, 1]) > 0.05 * np.abs(dx_[:, 1]).max()), 0] - 5.0
            dx_ = dx_[(dx_[:, 0] >= t0) & (dx_[:, 0] < t0 + dur)]; dy_ = dy_[(dy_[:, 0] >= t0) & (dy_[:, 0] < t0 + dur)]
        out.append((name,) + _pair(dx_[:, 1] * sc, dy_[:, 1] * sc, dx_[1, 0] - dx_[0, 0], dy_[1, 0] - dy_[0, 0], dt, tail))
    return out
