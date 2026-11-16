function estv = state_estimator_step(obsv, mode)
% STATE_ESTIMATOR_STEP  제어기용 상태 추정.
%  'ideal' (1차 개발): 센서 지연을 거쳐 도착한 플랜트 내부 상태 사본을 그대로 쓴다.
%           실제 센서 제어의 완성이 아니며, 결과는 '이상적 상태정보 조건'으로 표시한다.
%  관측기/필터(2차, 계획서 10절)는 아직 구현하지 않았다.
if nargin < 2, mode = 'ideal'; end
switch mode
    case 'ideal'
        estv = obsv;
    otherwise
        error('state_estimator_step: %s 미구현 (계획서 10절 2차 단계)', mode);
end
end
