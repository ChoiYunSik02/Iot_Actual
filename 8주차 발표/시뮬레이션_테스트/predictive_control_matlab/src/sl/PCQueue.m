classdef PCQueue < PCStageBase
    % PCQueue  CommandQueue: (cmdv 8) → relv 6  (command_queue_step)
    methods (Access = protected)
        function St = initStage(~)
            St = command_queue_step([], [], []);
        end
        function relv = stepImpl(obj, cmdv)
            [obj.St, relv] = command_queue_step(obj.St, cmdv, obj.i);
            obj.i = obj.i + 1;
        end
        function L = stageLog(obj, L)
            L.queue = struct('n_expired', obj.St.n_expired, 'n_applied', obj.St.n_applied);
        end
        function n = getNumInputsImpl(~), n = 1; end
        function n = getNumOutputsImpl(~), n = 1; end
        function s = getOutputSizeImpl(~), s = [6 1]; end
    end
end
