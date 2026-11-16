function t = out_tag()
% OUT_TAG  결과 파일 이름 꼬리표: Octave 예비 실행은 '_octave'를 붙여 MATLAB 결과와 섞이지 않게 한다.
if exist('OCTAVE_VERSION', 'builtin') > 0, t = '_octave'; else, t = ''; end
end
