from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.geodetics import gps2dist_azimuth
import numpy as np
c = Client("EARTHSCOPE")
evs = {"pohang":   (UTCDateTime("2017-11-15T05:29:31"), 36.109, 129.366),
       "gyeongju": (UTCDateTime("2016-09-12T11:32:54"), 35.769, 129.188)}
for name,(t0,la,lo) in evs.items():
    st = c.get_waveforms("KS","BUS2","*","BH?", t0-20, t0+120)
    rinv = c.get_stations(network="KS",station="BUS2",channel="BH?",level="response",starttime=t0,endtime=t0+1)
    stages = len(rinv[0][0][0].response.response_stages)
    print(name, "response stages:", stages, "| sensitivity:", rinv[0][0][0].response.instrument_sensitivity.value)
    raw = {tr.stats.channel: abs(tr.data).max() for tr in st}
    st.detrend("demean"); st.taper(0.05)
    if stages > 0:
        st.remove_response(inventory=rinv, output="ACC", pre_filt=(0.05,0.1,8,9.5)); how="full response"
    else:   # 스테이지 정보가 없으면 감도(평탄 응답)로 속도 환산 후 미분
        for tr in st:
            sens = rinv.select(channel=tr.stats.channel)[0][0][0].response.instrument_sensitivity.value
            tr.data = tr.data.astype(float)/sens
        st.differentiate(); st.filter("bandpass",freqmin=0.1,freqmax=8,corners=4,zerophase=True); how="sensitivity only"
    print("  correction:", how)
    inv = c.get_stations(network="KS",station="BUS2",level="station",starttime=t0,endtime=t0+1)
    s = inv[0][0]; d = gps2dist_azimuth(la,lo,s.latitude,s.longitude)[0]/1e3
    print(name, f"dist {d:.1f} km", "raw max counts", raw)
    for tr in st.select(channel="BH[NE]"):
        a = tr.data; dt = tr.stats.delta
        print("  ",tr.stats.channel, f"dt {dt}", f"PGA {abs(a).max()/9.81:.4f} g", f"t_peak {np.argmax(abs(a))*dt-20:.1f}s after origin")
        t = np.arange(len(a))*dt - 20   # 0 = 진원시
        np.savetxt(f"{name}_BUS2_{tr.stats.channel}.txt", np.c_[t,a], fmt="%.4f %.6e",
                   header=f"KS.BUS2 {tr.stats.channel} {name} origin {t0} dist {d:.1f} km | t[s from origin]  acc[m/s^2] | IRIS FDSN, response removed, 0.1-8 Hz")
