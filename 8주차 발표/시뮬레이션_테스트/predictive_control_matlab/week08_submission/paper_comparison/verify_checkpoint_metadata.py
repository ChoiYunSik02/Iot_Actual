# -*- coding: utf-8 -*-
"""노트북에서 쓴 checkpoint 메타데이터(JSON)와 저장소 사본의 내용 동일성 확인 (v3 검토).
노트북 hash는 checkpoint_hashes.json(PR 단계 기록). 저장소 사본은 git 줄바꿈 정규화(LF)를 거쳤다.
확인 1: 저장소 사본의 줄바꿈을 CRLF로 바꾼 바이트의 SHA-256 앞 16자리가 노트북 hash와 같은지 (바이트 단위 재현)
확인 2: 두 형태를 JSON으로 파싱해 객체가 같은지 (키·값 전체)
"""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); MAT = os.path.abspath(os.path.join(HERE, '..', '..'))
H = json.load(open(os.path.join(HERE, 'checkpoint_hashes.json'), encoding='utf-8'))['files']
ok = True
for key in ('models_torch_pilot8_seed8401_json', 'models_joint_scorer_seed8401_json'):
    info = H[key]; path = os.path.join(MAT, info['path'])
    raw = open(path, 'rb').read()
    crlf = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    h_raw, h_crlf = hashlib.sha256(raw).hexdigest()[:16], hashlib.sha256(crlf).hexdigest()[:16]
    same_parse = json.loads(raw.decode('utf-8')) == json.loads(crlf.decode('utf-8'))
    nk = len(json.loads(raw.decode('utf-8')))
    m = 'LF 그대로' if h_raw == info['sha256_16'] else ('CRLF로 바꾸면' if h_crlf == info['sha256_16'] else '불일치')
    print(f"{info['path']}: 노트북 {info['sha256_16']} ({info['bytes']:.0f} B) | 저장소 {h_raw} ({len(raw)} B), CRLF 변환 {h_crlf} ({len(crlf)} B) → 바이트 재현: {m} | JSON 파싱 동일: {same_parse} (키 {nk}개)")
    ok = ok and m != '불일치' and same_parse
print('결과:', '내용 동일 (줄바꿈만 다름 또는 완전 동일)' if ok else '불일치 — 확인 필요')
sys.exit(0 if ok else 1)
