function [ag, t, info] = w5_record(name, pga, dt, T, naxes)
%W5_RECORD  실관측 기록을 읽어 dt 로 재샘플링하고 목표 PGA [g] 로 스케일합니다.
%
%   name  : 'pohang' | 'gyeongju' | 'elcentro'   (records/README.md 참고)
%   naxes : 1 (기본, 한 축) | 2 (X·Y 두 성분 → ag 가 N×2)
%   ag    : 지반가속도 [m/s^2],  t : 0 ~ T [s]
%   info.tS : S파 도착 시각 [s] (경보 기준점)
%             한국 기록 — 진앙거리 / 3.5 km/s
%             El Centro — 진원시 정보가 없어 |ag| 가 처음 0.05g 를 넘는 시각
%
%   2축: 두 성분에 같은 배율을 곱해 더 큰 성분의 PGA 가 목표 PGA 가 되도록 스케일.
%        한국 기록은 P파 도착 5 s 전부터 자름 (충주 164 km 는 S파가 진원 후 47 s 에 도착)
%        경주는 부산 동서 성분이 포화돼 충주(KS.CHJ2) 기록을 사용

if nargin < 5, naxes = 1; end
here = fileparts(mfilename('fullpath'));
switch lower(name)
    case 'pohang'
        f = {'pohang_BUS2_BHE.txt','pohang_BUS2_BHN.txt'};  dist = 98.2;  unit = 1;
    case 'gyeongju'
        if naxes == 1, f = {'gyeongju_BUS2_BHN.txt'};  dist = 58.1;
        else,          f = {'gyeongju_CHJ2_BHE.txt','gyeongju_CHJ2_BHN.txt'};  dist = 163.9; end
        unit = 1;
    case 'elcentro'
        f = {'elcentro_NS.txt','elcentro_EW.txt'};  dist = NaN;  unit = 9.81;   % 원본 단위 g
    otherwise, error('w5_record:name', '알 수 없는 기록: %s', name);
end
f = f(1:naxes);

t0 = 0;                                         % 자르기 시작 시각 (진원시 기준)
if naxes == 2 && ~isnan(dist), t0 = dist/6.0 - 5; end

t  = (0:dt:T)';
ag = zeros(numel(t), naxes);
for k = 1:naxes
    d  = readmatrix(fullfile(here, 'records', f{k}), 'FileType', 'text', 'CommentStyle', '#');
    tr = d(:,1);  ar = d(:,2) * unit;
    if ~isnan(dist), keep = tr >= t0;  tr = tr(keep);  ar = ar(keep); end
    ag(:,k) = interp1(tr - tr(1), ar, t, 'pchip', 0);    % 기록 끝 이후는 0
    ag(:,k) = ag(:,k) - mean(ag(:,k));
end
ag = ag / max(abs(ag(:))) * pga * 9.81;

if isnan(dist)
    info.tS = t(find(max(abs(ag),[],2) >= 0.05*9.81, 1));
else
    info.tS = dist/3.5 - t0;
end
info.dist = dist;  info.file = f;  info.t0 = t0;
end
