classdef PCSensor < PCStageBase
    % PCSensor  SensorAndLatency: (x 276, Avec 9, ag_now 2) → obsv 296  (sensor_step)
    methods (Access = protected)
        function St = initStage(obj)
            St = sensor_step([], [], [], [], [], obj.P);
        end
        function obsv = stepImpl(obj, x, Avec, ag_now)
            S = struct('u', x(1:92), 'v', x(93:184), 'a', x(185:276), 'i', obj.i);
            [obj.St, obsv] = sensor_step(obj.St, S, Avec, ag_now, obj.i, obj.P);
            obj.i = obj.i + 1;
        end
        function n = getNumInputsImpl(~), n = 3; end
        function n = getNumOutputsImpl(~), n = 1; end
        function s = getOutputSizeImpl(~), s = [296 1]; end
    end
end
