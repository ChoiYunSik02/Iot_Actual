# -*- coding: utf-8 -*-
"""작은 LSTM 미래 파형 예측기 — PyTorch smoke 학습 (Deep Learning Toolbox 대체, 연결 시험용).

계획서 8절과 같은 구성:
  입력 3 x 500 (정규화 X, 정규화 Y, 마스크), 출력 800 = [X(1..400); Y(1..400)] (정규화)
  LSTM(64, 마지막 상태) → FC(128) → ReLU → FC(800), MSE, Adam 1e-3, batch 32, 기울기 노름 1,
  매 epoch 검증, 검증 손실 10회 연속 개선 없으면 종료, 최저 검증 손실 모델 사용.
입력·정답·분할은 MATLAB build_forecast_dataset이 만든 파일을 그대로 읽는다 (Python에서 다시 만들지 않음).
  - MATLAB -v7.3 (HDF5): h5py로 읽음.  X: (N, 500, 3) = (B, T, C), Y: (N, 800)
  - Octave -v7: scipy.io로 읽음 (클라우드 예비 점검용)
smoke(연결 시험)와 8주차 소규모 pilot(--stage pilot8)에 쓴다.

사용:
  python pc_lstm.py --dataset ../data/forecast_dataset_smoke.mat --out ../models/torch_smoke_seed8401 --epochs 10 --seed 8401
결과:
  <out>.pt            state_dict
  <out>.json          scaler, 순서, 학습 기록, 검증 MSE, 버전, 자료 해시
  <out>_weights.mat   MATLAB 재구현(lstm_forward.m)용 가중치
"""
import argparse, hashlib, json, os, platform, sys, time
import numpy as np
import torch
from torch import nn

H_DEFAULT, FC1_DEFAULT, OUT_DEFAULT = 64, 128, 800


class Forecaster(nn.Module):
    def __init__(self, hidden=H_DEFAULT, fc1=FC1_DEFAULT, out=OUT_DEFAULT):
        super().__init__()
        self.lstm = nn.LSTM(input_size=3, hidden_size=hidden, batch_first=True)
        self.fc1 = nn.Linear(hidden, fc1)
        self.fc2 = nn.Linear(fc1, out)

    def forward(self, x):                      # x: (B, T, 3)
        _, (h, _) = self.lstm(x)               # 창 기반 stateless: 매 호출 초기 상태 0
        return self.fc2(torch.relu(self.fc1(h[-1])))


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


def load_dataset(path):
    """MATLAB/Octave 자료 → dict(train/val/real_val/real_diag: (X (N,T,C) float32, Y (N,800) float32), scaler)."""
    out = {}
    try:
        import h5py
        f = h5py.File(path, 'r')                   # MATLAB -v7.3
        for sp in ('train', 'val', 'real_val', 'real_diag'):
            g = f['W'][sp]
            X = np.array(g['X'], dtype=np.float32)   # MATLAB 3x500xN → h5 (N,500,3)
            Y = np.array(g['Y'], dtype=np.float32)   # MATLAB 800xN  → h5 (N,800)
            if X.ndim != 3:                          # 빈 분할 (MATLAB 0x0 등)
                X = np.zeros((0, 500, 3), np.float32); Y = np.zeros((0, 800), np.float32)
            out[sp] = (X, Y)
        sc = f['scaler']
        out['scaler'] = {'mu': np.array(sc['mu']).ravel().tolist(), 'sd': np.array(sc['sd']).ravel().tolist()}
        out['format'] = 'matlab-v7.3'
        return out
    except OSError:
        pass
    import scipy.io as sio                           # Octave -v7 (예비 점검)
    m = sio.loadmat(path, squeeze_me=True, struct_as_record=False)
    for sp in ('train', 'val', 'real_val', 'real_diag'):
        g = getattr(m['W'], sp)
        X = np.asarray(g.X, dtype=np.float32); Y = np.asarray(g.Y, dtype=np.float32)
        if X.ndim == 3:
            X = np.transpose(X, (2, 1, 0)); Y = Y.T   # 3x500xN → N,500,3 ; 800xN → N,800
        else:
            X = np.zeros((0, 500, 3), np.float32); Y = np.zeros((0, 800), np.float32)
        out[sp] = (X, Y)
    out['scaler'] = {'mu': np.atleast_1d(m['scaler'].mu).tolist(), 'sd': np.atleast_1d(m['scaler'].sd).tolist()}
    out['format'] = 'octave-v7'
    return out


def evaluate(model, X, Y, bs=512, dev='cpu'):
    model.eval(); tot = 0.0; n = 0
    with torch.no_grad():
        for k in range(0, len(X), bs):
            xb = torch.from_numpy(X[k:k+bs]).to(dev); yb = torch.from_numpy(Y[k:k+bs]).to(dev)
            tot += float(((model(xb) - yb) ** 2).sum()); n += yb.numel()
    return tot / max(n, 1)


def numpy_forward(sd, x):
    """PyTorch와 같은 식의 numpy 순전파 (MATLAB lstm_forward.m과 같은 식). x: (T, 3)."""
    Wih, Whh = sd['lstm.weight_ih_l0'], sd['lstm.weight_hh_l0']
    b = sd['lstm.bias_ih_l0'] + sd['lstm.bias_hh_l0']; Hn = Whh.shape[1]
    h = np.zeros(Hn); c = np.zeros(Hn); sig = lambda z: 1 / (1 + np.exp(-z))
    for t in range(x.shape[0]):
        g = Wih @ x[t] + Whh @ h + b
        i, f, gg, o = sig(g[:Hn]), sig(g[Hn:2*Hn]), np.tanh(g[2*Hn:3*Hn]), sig(g[3*Hn:])
        c = f * c + i * gg; h = o * np.tanh(c)
    z = np.maximum(sd['fc1.weight'] @ h + sd['fc1.bias'], 0)
    return sd['fc2.weight'] @ z + sd['fc2.bias']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--epochs', type=int, default=10); ap.add_argument('--seed', type=int, default=8401)
    ap.add_argument('--batch', type=int, default=32); ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--patience', type=int, default=10); ap.add_argument('--threads', type=int, default=0)
    ap.add_argument('--device', default='cpu', help="cpu | cuda | auto (cuda 있으면 사용)")
    ap.add_argument('--stage', default='smoke')
    ap.add_argument('--overfit_check', type=int, default=0, help='N>0: 학습 전 train 앞 64창에 N스텝 과적합 시험 (파이프라인 점검, 일반화 증거 아님)')
    a = ap.parse_args()
    torch.manual_seed(a.seed); np.random.seed(a.seed)
    if a.threads > 0: torch.set_num_threads(a.threads)
    D = load_dataset(a.dataset)
    Xtr, Ytr = D['train']; Xv, Yv = D['val']
    print(f"자료 {D['format']}: train {Xtr.shape}, val {Xv.shape}, real_val {D['real_val'][0].shape}", flush=True)
    dev = 'cuda' if (a.device == 'auto' and torch.cuda.is_available()) or a.device == 'cuda' else 'cpu'
    # 무진동(영점) 창 비율: 정답 미래 4 s 정규화 RMS < 0.1 인 창
    rms_tr = np.sqrt((Ytr.astype(np.float64)**2).mean(axis=1)); quiet = float((rms_tr < 0.1).mean())
    print(f"정답 RMS<0.1(무진동) 창 비율 {quiet:.3f}, 정답 RMS 중앙값 {np.median(rms_tr):.3f}", flush=True)
    ofc = None
    if a.overfit_check > 0:                     # 작은 부분집합 과적합 시험: 손실이 줄어야 파이프라인이 정상
        torch.manual_seed(a.seed); m0 = Forecaster().to(dev); o0 = torch.optim.Adam(m0.parameters(), lr=a.lr)
        xb = torch.from_numpy(Xtr[:64]).to(dev); yb = torch.from_numpy(Ytr[:64]).to(dev); l0 = None
        for st in range(a.overfit_check):
            o0.zero_grad(); l = nn.functional.mse_loss(m0(xb), yb); l.backward(); o0.step()
            if l0 is None: l0 = float(l.detach())
        ofc = {'n_windows': 64, 'steps': a.overfit_check, 'loss_first': l0, 'loss_last': float(l.detach()), 'pass': float(l) <= 0.5*l0}
        print(f"과적합 시험 64창 {a.overfit_check}스텝: 손실 {l0:.4f} → {float(l.detach()):.4f} → {'통과' if ofc['pass'] else '실패'}", flush=True)
        del m0, o0
        torch.manual_seed(a.seed)
    model = Forecaster().to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    g = torch.Generator().manual_seed(a.seed)
    hist = []; best = (np.inf, None, -1); bad = 0; t0 = time.time()
    for ep in range(1, a.epochs + 1):
        model.train(); perm = torch.randperm(len(Xtr), generator=g).numpy(); tl = 0.0; nb = 0
        for k in range(0, len(perm) - a.batch + 1, a.batch):          # 끝 자투리 batch는 버림 (MATLAB minibatch와 같게)
            idx = perm[k:k+a.batch]
            xb = torch.from_numpy(Xtr[idx]).to(dev); yb = torch.from_numpy(Ytr[idx]).to(dev)
            opt.zero_grad(); loss = nn.functional.mse_loss(model(xb), yb); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
            tl += float(loss); nb += 1
        vl = evaluate(model, Xv, Yv, dev=dev)
        hist.append({'epoch': ep, 'train_loss': tl / max(nb, 1), 'val_mse': vl, 'elapsed_s': time.time() - t0})
        print(f"epoch {ep:3d}  train {tl/max(nb,1):.4f}  val {vl:.4f}  {time.time()-t0:.0f} s", flush=True)
        if vl < best[0]:
            best = (vl, {k: v.detach().clone() for k, v in model.state_dict().items()}, ep); bad = 0
        else:
            bad += 1
            if bad >= a.patience: break
    model = model.cpu(); model.load_state_dict({k: v.cpu() for k, v in best[1].items()})
    sd = {k: v.numpy().astype(np.float64) for k, v in model.state_dict().items()}
    # 단위시험: numpy 순전파 = torch, 출력 순서 [X(1..400); Y(1..400)]
    xs = Xv[:5] if len(Xv) else Xtr[:5]
    with torch.no_grad():
        yt = model(torch.from_numpy(xs)).numpy()
    yn = np.stack([numpy_forward(sd, x.astype(np.float64)) for x in xs])
    parity = float(np.max(np.abs(yt - yn)))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    torch.save(model.state_dict(), a.out + '.pt')
    import scipy.io as sio
    sio.savemat(a.out + '_weights.mat', {
        'W_ih': sd['lstm.weight_ih_l0'], 'W_hh': sd['lstm.weight_hh_l0'],
        'b': (sd['lstm.bias_ih_l0'] + sd['lstm.bias_hh_l0']).reshape(-1, 1),
        'W1': sd['fc1.weight'], 'b1': sd['fc1.bias'].reshape(-1, 1), 'W2': sd['fc2.weight'], 'b2': sd['fc2.bias'].reshape(-1, 1),
        'mu': np.array(D['scaler']['mu']), 'sd': np.array(D['scaler']['sd'])})
    meta = {'stage': a.stage, 'device': dev, 'patience': a.patience, 'seed': a.seed, 'epochs_max': a.epochs, 'best_epoch': best[2], 'val_mse': best[0],
            'history': hist, 'train_s': time.time() - t0, 'n_train': int(len(Xtr)), 'n_val': int(len(Xv)),
            'scaler': D['scaler'], 'order_in': 'X: (B, T=500, C=3) = [zX, zY, mask]', 'order_out': '[zX(1..400); zY(1..400)]',
            'gate_order': 'PyTorch LSTM i, f, g, o', 'numpy_parity_maxabs': parity,
            'dataset': os.path.abspath(a.dataset), 'dataset_sha16': sha256(a.dataset), 'dataset_format': D['format'],
            'torch': torch.__version__, 'numpy': np.__version__, 'python': sys.version.split()[0], 'platform': platform.platform(),
            'threads': torch.get_num_threads(), 'quiet_frac_train': quiet, 'overfit_check': ofc}
    with open(a.out + '.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"최저 검증 MSE {best[0]:.4f} (epoch {best[2]}), numpy 대조 {parity:.2e}, 학습 {meta['train_s']:.0f} s → {a.out}.pt", flush=True)


if __name__ == '__main__':
    main()
