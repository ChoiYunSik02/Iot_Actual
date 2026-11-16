classdef PCEstimator < PCStageBase
    % PCEstimator  StateEstimator: (obsv 296) → estv 296  (state_estimator_step, 1차: 이상적 상태정보)
    methods (Access = protected)
        function estv = stepImpl(obj, obsv)
            estv = state_estimator_step(obsv, 'ideal');
            obj.i = obj.i + 1;
        end
        function n = getNumInputsImpl(~), n = 1; end
        function n = getNumOutputsImpl(~), n = 1; end
        function s = getOutputSizeImpl(~), s = [296 1]; end
    end
end
