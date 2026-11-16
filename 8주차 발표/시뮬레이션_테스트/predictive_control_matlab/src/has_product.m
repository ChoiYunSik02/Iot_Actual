function tf = has_product(name)
% HAS_PRODUCT  설치 제품 + 라이선스 확인 ('Simulink' | 'Deep Learning Toolbox').
%  exist('new_system','file')처럼 내장 함수 이름으로 확인하면 내장 함수는 0이 나오므로 쓰지 않는다.
if exist('OCTAVE_VERSION', 'builtin') > 0, tf = false; return; end
feat = struct('Simulink', 'Simulink', 'Deep_Learning_Toolbox', 'Neural_Network_Toolbox');
key = strrep(name, ' ', '_');
v = ver;
tf = any(strcmp({v.Name}, name)) && license('test', feat.(key));
end
