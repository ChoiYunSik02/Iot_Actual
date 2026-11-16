classdef PCPlant < matlab.System
    % PCPlant  Plant30Story: 30층 구조 + 장치 상태 한 스텝 적분 (plant_step).
    %  입력 ag_next(2), dev(3) → 출력 x(276) = [u; v; a] (현재 스텝 상태), top(3) = [ux; uy; th]
    %  직접 통과 없음(출력은 이전 갱신 결과) → 대수 루프 없음.
    properties (Nontunable)
        CtxVar = 'pc_ctx'
        Ts = 0.01          % 샘플 시간 [s] (블록 대화상자 기본 이름과 겹치지 않게 Ts)
    end
    properties (Access = private)
        P; S; hasDev
    end
    methods (Access = protected)
        function setupImpl(obj)
            ctx = pc_sl_ctx(obj.CtxVar); obj.P = ctx.P; obj.hasDev = ~strcmp(ctx.M.select, 'U');
            [~, obj.S] = plant_init(ctx.cfg, ctx.P.dt);
        end
        function resetImpl(obj)
            obj.S.u(:) = 0; obj.S.v(:) = 0; obj.S.a(:) = 0; obj.S.i = 0;
        end
        function [x, top] = outputImpl(obj, ~, ~)
            x = [obj.S.u; obj.S.v; obj.S.a];
            top = [obj.S.u(obj.P.tx); obj.S.u(obj.P.ty); obj.S.u(obj.P.tth)];
        end
        function updateImpl(obj, ag_next, dev)
            obj.S = plant_step(obj.S, ag_next, dev, obj.P, obj.hasDev);
        end
        function [f1, f2] = isInputDirectFeedthroughImpl(~, ~, ~), f1 = false; f2 = false; end
        function n = getNumInputsImpl(~), n = 2; end
        function n = getNumOutputsImpl(~), n = 2; end
        function [s1, s2] = getOutputSizeImpl(~), s1 = [276 1]; s2 = [3 1]; end
        function [d1, d2] = getOutputDataTypeImpl(~), d1 = 'double'; d2 = 'double'; end
        function [c1, c2] = isOutputComplexImpl(~), c1 = false; c2 = false; end
        function [f1, f2] = isOutputFixedSizeImpl(~), f1 = true; f2 = true; end
        function sts = getSampleTimeImpl(obj), sts = createSampleTime(obj, 'Type', 'Discrete', 'SampleTime', obj.Ts); end
    end
end
