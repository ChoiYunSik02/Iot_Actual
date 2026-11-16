classdef PCForecaster < PCStageBase
    % PCForecaster  Forecaster: (bufv 1503) → fcv 803  (forecaster_step). 예측기 없음(R/FIX/U)이면 0 출력.
    methods (Access = protected)
        function St = initStage(obj)
            c = obj.ctx;
            St = forecaster_step(struct('kind', c.M.forecaster, 'model', c.model, 'preview', c.preview), [], [], obj.P);
        end
        function fcv = stepImpl(obj, bufv)
            if strcmp(obj.ctx.M.forecaster, 'none')
                fcv = zeros(803, 1);
            else
                [obj.St, fcv] = forecaster_step(obj.St, bufv, obj.i, obj.P);
            end
            obj.i = obj.i + 1;
        end
        function L = stageLog(obj, L)
            L.forecast = struct('log', obj.St.log, 'miss_busy', obj.St.miss_busy, 'miss_deadline', obj.St.miss_deadline);
        end
        function n = getNumInputsImpl(~), n = 1; end
        function n = getNumOutputsImpl(~), n = 1; end
        function s = getOutputSizeImpl(~), s = [803 1]; end
    end
end
