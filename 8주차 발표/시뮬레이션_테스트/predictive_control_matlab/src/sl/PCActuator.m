classdef PCActuator < PCStageBase
    % PCActuator  Actuators: (relv 6) → dev 3, Avec 9  (actuator_step). U(장치 없음)이면 dev = 0.
    methods (Access = protected)
        function St = initStage(obj)
            St = actuator_step([], [], [], obj.P);
        end
        function [dev, Avec] = stepImpl(obj, relv)
            if strcmp(obj.ctx.M.select, 'U')
                dev = zeros(3, 1);
            else
                [obj.St, dev] = actuator_step(obj.St, relv, obj.i, obj.P);
            end
            Avec = act_pack(obj.St);
            obj.i = obj.i + 1;
        end
        function n = getNumInputsImpl(~), n = 1; end
        function n = getNumOutputsImpl(~), n = 2; end
        function [s1, s2] = getOutputSizeImpl(~), s1 = [3 1]; s2 = [9 1]; end
    end
end
