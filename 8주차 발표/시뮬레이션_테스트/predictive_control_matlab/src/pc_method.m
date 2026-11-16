function M = pc_method(cfg, name, ov)
% PC_METHOD  계획서 11절 비교군 정의.
%  name : 'U' | 'R' | 'FIX' | 'SIMPLE-zero' | 'SIMPLE-persistence' | 'SIMPLE-var'
%         | 'AI-C1' | 'AI-C2' | 'AI-ideal-C1' | 'AI-ideal-C2' | 'PREVIEW-C1' | 'PREVIEW-C2'
%         | 'AIPY-C1' (PyTorch, Python 호출) | 'AINAT-C1' (같은 가중치 MATLAB 재구현)
%         | 'J-zero' 'J-persistence' 'J-AIF'(AI 예측·전체 평가) 'J-AI'(AI 예측·점수망 top 3) 'J-PREVIEW' 'C1J-AI'(밸브 R) — 8주차 v2
%  ov   : (선택) 덮어쓸 필드 struct. 예) struct('extra_info_s',0.5) 또는 struct('forecast_s',0.05)
%  지연(초): sensor_s·comm_s는 모든 방식 공통, extra_info_s는 민감도용 추가 정보처리 지연,
%           select_s·forecast_s는 그 방식의 계산 시간(실측값, 없으면 0으로 두고 unmeasured 표시).
if nargin < 3, ov = struct(); end
L = cfg.latency; cs = L.compute_s;
M = struct('name', name, 'select', '', 'forecaster', 'none', 'sensor_s', L.sensor_s, 'comm_s', L.comm_s, ...
           'extra_info_s', L.extra_info_s, 'select_s', 0, 'forecast_s', 0, 'unmeasured', {{}}, ...
           'timing_mode', L.timing_mode, 'inject_select_s', L.inject_select_s, 'inject_forecast_s', L.inject_forecast_s, 'model_file', '');
switch name
    case 'U',   M.select = 'U';
    case 'R',   M.select = 'R';   M = getc(M, cs, 'R', 'select_s');
    case 'FIX', M.select = 'FIX'; M = getc(M, cs, 'R', 'select_s');
    otherwise
        parts = regexp(name, '-', 'split');
        switch parts{1}
            case 'SIMPLE'
                M.select = 'C1'; M.forecaster = parts{2};
            case {'AIPY', 'AINAT'}                     % PyTorch smoke 모델: Python 호출 / MATLAB 재구현 (연결 시험용)
                if strcmp(parts{1}, 'AIPY'), M.forecaster = 'torch'; else, M.forecaster = 'lstmnat'; end
                M.select = parts{end};
            case 'AI'
                M.forecaster = 'lstm';
                M.select = parts{end};
                if any(strcmp(parts, 'ideal')), M.extra_info_s = 0; end
            case 'PREVIEW'
                M.select = parts{2}; M.forecaster = 'preview';
            case {'J', 'C1J'}                          % 8주차 v2 공동 선택: J-zero | J-persistence | J-AIF | J-AI | J-PREVIEW | C1J-AI
                M.select = 'J'; M.jscorer = strcmp(parts{2}, 'AI') && strcmp(parts{1}, 'J');
                M.jvalve = 'joint'; if strcmp(parts{1}, 'C1J'), M.jvalve = 'law'; end
                switch parts{2}
                    case {'AI', 'AIF'}, M.forecaster = 'lstmnat';
                    case 'PREVIEW', M.forecaster = 'preview';
                    otherwise, M.forecaster = parts{2};
                end
            otherwise
                error('pc_method: 모르는 방식 %s', name);
        end
        M = getc(M, cs, ['select_' M.select], 'select_s');
        if strcmp(M.select, 'J'), M = getc(M, cs, 'select_JV', 'selectV_s'); end
        M = getc(M, cs, ['forecast_' M.forecaster], 'forecast_s');
        if any(strcmp(parts, 'ideal')), M.select_s = 0; M.forecast_s = 0; M.unmeasured = {}; end
end
% 원래 시각 R 경로용 R 계산 예산 (미측정이면 선택 예산과 같게 두고 미측정 목록에는 넣지 않음)
if isfield(cs, 'R') && ~isempty(cs.R), M.R_s = cs.R; else, M.R_s = M.select_s; end
if any(strcmp(M.select, {'R', 'FIX'})), M.R_s = M.select_s; end
fn = fieldnames(ov);
for k = 1:numel(fn), M.(fn{k}) = ov.(fn{k}); end
if any(strcmp(M.select, {'R', 'FIX'})), M.R_s = M.select_s; end
if strcmp(M.select, 'J') && isfield(ov, 'select_s') && ~isfield(ov, 'selectV_s'), M.selectV_s = M.select_s; end
if isfield(ov, 'select_s'), M.unmeasured = M.unmeasured(~strncmp(M.unmeasured, 'select_', 7) & ~strcmp(M.unmeasured, 'R')); end
if isfield(ov, 'forecast_s'), M.unmeasured = M.unmeasured(~strncmp(M.unmeasured, 'forecast_', 9)); end
end

function M = getc(M, cs, key, field)
% 실측 계산시간을 M.(field)에 넣는다. 없으면 0으로 두고 미측정 목록에 남긴다.
% (예전 '[M.x, M] = getc(...)' 형태는 두 번째 출력이 첫 번째 대입을 덮어써 값이 항상 0이 되는 버그가 있었다)
if isfield(cs, key) && ~isempty(cs.(key))
    M.(field) = cs.(key);
else
    M.(field) = 0; M.unmeasured{end+1} = key;
end
end
