# -*- coding: utf-8 -*-
"""X·Y 2축 실험용 한국 기록 내려받기 (ObsPy 필요: pip install obspy).

  포항 2017 — KS.BUS2 부산 (98 km), 동서·남북 모두 포화 없음
  경주 2016 — KS.CHJ2 충주 (164 km), 부산 관측소는 동서 성분이 포화(clip)돼 충주로 대체

처리: 감도로 속도 환산 → 미분 → 0.1–8 Hz 대역통과 (응답 스테이지 정보가 없어서)
출력: <이름>_<관측소>_<성분>.txt  (t [s, 진원시=0], 가속도 [m/s^2])
"""
import numpy as np
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.geodetics import gps2dist_azimuth

CLIP = 2 ** 23          # 24비트 디지타이저 한계 [counts]
c = Client("EARTHSCOPE")
evs = {"pohang":   (UTCDateTime("2017-11-15T05:29:31"), 36.109, 129.366, "BUS2"),
       "gyeongju": (UTCDateTime("2016-09-12T11:32:54"), 35.769, 129.188, "CHJ2")}

for name, (t0, la, lo, sta) in evs.items():
    st = c.get_waveforms("KS", sta, "*", "BH?", t0 - 20, t0 + 150).select(channel="BH[NE]")
    inv = c.get_stations(network="KS", station=sta, channel="BH?", level="response",
                         starttime=t0, endtime=t0 + 1)
    s0 = inv[0][0]
    d = gps2dist_azimuth(la, lo, s0.latitude, s0.longitude)[0] / 1e3
    for tr in st:
        raw = int(abs(tr.data).max())
        assert raw < CLIP, f"{name} {sta} {tr.stats.channel} 포화 의심 ({raw} counts)"
        sens = inv.select(channel=tr.stats.channel)[0][0][0].response.instrument_sensitivity.value
        tr.data = tr.data.astype(float) / sens
    st.detrend("demean"); st.taper(0.05)
    st.differentiate()
    st.filter("bandpass", freqmin=0.1, freqmax=8, corners=4, zerophase=True)
    for tr in st:
        a = tr.data; dt = tr.stats.delta
        t = np.arange(len(a)) * dt - 20
        f = f"{name}_{sta}_{tr.stats.channel}.txt"
        np.savetxt(f, np.c_[t, a], fmt="%.4f %.6e",
                   header=f"KS.{sta} {tr.stats.channel} {name} origin {t0} dist {d:.1f} km | "
                          f"t[s from origin]  acc[m/s^2] | EarthScope FDSN, sensitivity-corrected, 0.1-8 Hz")
        print(f, f"dist {d:.1f} km", f"PGA {abs(a).max()/9.81:.4f} g")
