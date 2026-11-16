classdef PCBuffer < PCStageBase
    % PCBuffer  ObservationBuffer: (obsv 296) → bufv 1503  (obsbuffer_step)
    methods (Access = protected)
        function St = initStage(obj)
            St = obsbuffer_step([], [], obj.P);
        end
        function bufv = stepImpl(obj, obsv)
            [obj.St, bufv] = obsbuffer_step(obj.St, obsv, obj.P);
            obj.i = obj.i + 1;
        end
        function n = getNumInputsImpl(~), n = 1; end
        function n = getNumOutputsImpl(~), n = 1; end
        function s = getOutputSizeImpl(~), s = [1503 1]; end
    end
end
