function [QS, relv] = command_queue_step(QS, cmdv, i)
% COMMAND_QUEUE_STEP  연산·통신·갱신 대기 후 지령 적용 (정수 스텝).
%  cmdv = [has_any; has_f; f; has_th; th; has_k; kappa; apply_step]  (selector_step 출력, 길이 8)
%  relv = [has_f; f; has_th; th; has_k; kappa]  — 이번 스텝(apply_step == i)에 장치로 내보내는 지령
%  apply_step < i 인 지령(늦게 도착)은 적용하지 않고 만료로 센다.
if isempty(QS)
    QS = struct('items', zeros(0,7), 'n_expired', 0, 'n_applied', 0);
    relv = zeros(6,1);
    return;
end
if cmdv(1) > 0.5
    QS.items(end+1,:) = [cmdv(8), cmdv(2:7)'];
end
relv = zeros(6,1);
if isempty(QS.items), return; end
late = QS.items(:,1) < i;
QS.n_expired = QS.n_expired + sum(late);
now_ = find(QS.items(:,1) == i);
for k = now_(:)'                      % 같은 스텝 지령은 나중 것이 덮어씀 (항목별)
    c = QS.items(k, 2:7);
    if c(1) > 0.5, relv(1:2) = c(1:2)'; end
    if c(3) > 0.5, relv(3:4) = c(3:4)'; end
    if c(5) > 0.5, relv(5:6) = c(5:6)'; end
end
QS.n_applied = QS.n_applied + numel(now_);
QS.items(late | QS.items(:,1) == i, :) = [];
end
