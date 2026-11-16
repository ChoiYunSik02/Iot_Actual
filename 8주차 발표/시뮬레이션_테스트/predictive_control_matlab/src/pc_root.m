function root = pc_root()
% PC_ROOT  predictive_control_matlab 폴더 절대 경로.
root = fileparts(fileparts(mfilename('fullpath')));
% 산출물 폴더 (빈 폴더는 git에 없을 수 있으므로 만들어 둠)
for d = {'models', 'checkpoints', 'results', 'logs', 'report'}
    if ~exist(fullfile(root, d{1}), 'dir'), mkdir(fullfile(root, d{1})); end
end
end
