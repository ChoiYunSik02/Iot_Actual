function SC = load_scorer(path)
% LOAD_SCORER  python/train_joint_scorer.py 출력 <path>.json 읽기 (가중치·표준화 값).
J = jsondecode(fileread([path '.json']));
SC = struct('path', path, 'mu', J.mu(:)', 'sd', J.sd(:)', 'W1', J.W1, 'b1', J.b1(:)', 'W2', J.W2, 'b2', J.b2(:)', ...
            'W3', reshape(J.W3, 1, []), 'b3', J.b3, 'meta', rmfield(J, {'mu', 'sd', 'W1', 'b1', 'W2', 'b2', 'W3', 'b3'}));
end
