"""기존 점수망(98-128-64-1, ReLU, seed 8401)의 numpy 순전파 이식. 가중치·표준화 통계는 JSON 그대로 고정(재표준화 없음).
확인: JSON에 저장된 parity_X(50×98)에 대한 출력이 parity_y와 같은지."""
import json, numpy as np, sys
def load(path):
    d=json.load(open(path)); g=lambda k: np.array(d[k],float)
    return dict(mu=g('mu'),sd=g('sd'),W1=g('W1'),b1=g('b1'),W2=g('W2'),b2=g('b2'),W3=g('W3'),b3=float(d['b3'])),d
def forward(m,X):
    Z=(X-m['mu'])/m['sd']; h=np.maximum(Z@m['W1'].T+m['b1'],0); h=np.maximum(h@m['W2'].T+m['b2'],0); return h@m['W3']+m['b3']
if __name__=='__main__':
    m,d=load(sys.argv[1]); p=forward(m,np.array(d['parity_X'])); print('parity max abs diff',float(np.abs(p-np.array(d['parity_y'])).max()))
