function y = rank_joint_candidates(SC, X)
% RANK_JOINT_CANDIDATES  공동 후보 점수망 추론 (MATLAB 재구현, python/train_joint_scorer.py와 같은 식).
%  SC = load_scorer(경로): mu sd (표준화), W1 b1 W2 b2 W3 b3. 출력 y = 예측 상대 비용 J/J_R − 1 (작을수록 좋음).
Z = (X - SC.mu)./SC.sd;
H = max(0, Z*SC.W1' + SC.b1);
H = max(0, H*SC.W2' + SC.b2);
y = H*SC.W3' + SC.b3;
end
