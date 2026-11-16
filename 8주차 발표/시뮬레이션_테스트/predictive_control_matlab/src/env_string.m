function s = env_string()
% ENV_STRING  실행 환경 표시 (결과 파일마다 기록: MATLAB 판정과 Octave 예비를 구분).
if exist('OCTAVE_VERSION', 'builtin') > 0
    s = ['Octave ' OCTAVE_VERSION ' (예비)'];
else
    s = ['MATLAB ' version];
end
end
