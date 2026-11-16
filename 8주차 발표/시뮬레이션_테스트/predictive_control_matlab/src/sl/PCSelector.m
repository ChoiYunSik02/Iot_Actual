classdef PCSelector < PCStageBase
    % PCSelector  CommandSelector: (estv 296, fcv 803) → cmdv 8  (selector_step)
    methods (Access = protected)
        function St = initStage(obj)
            c = obj.ctx; St = selector_init(c.cfg, obj.P, c.M, c.nt);
        end
        function cmdv = stepImpl(obj, estv, fcv)
            [obj.St, cmdv] = selector_step(obj.St, estv, fcv, obj.i, obj.P);
            obj.i = obj.i + 1;
        end
        function L = stageLog(obj, L)
            L.timeline = obj.St.log(1:obj.St.nlog, :);
        end
        function n = getNumInputsImpl(~), n = 2; end
        function n = getNumOutputsImpl(~), n = 1; end
        function s = getOutputSizeImpl(~), s = [8 1]; end
    end
end
