classdef (Abstract) PCStageBase < matlab.System
    % PCStageBase  제어 쪽 서브시스템 블록의 공통 부분 (실행 맥락, 스텝 번호, 샘플 시간, 기록).
    %  서브클래스는 입력·출력 수가 고정된 stepImpl과 크기 함수, initStage를 정의한다.
    %  (입력 수를 속성으로 바꾸는 방식은 블록 추가 시점에 포트가 정해지지 않아 쓰지 않는다.)
    %  스텝 번호 i는 0부터 매 실행 1씩 증가한다(모든 블록이 같은 샘플 시간).
    properties (Nontunable)
        CtxVar = 'pc_ctx'
        Ts = 0.01          % 샘플 시간 [s] (블록 대화상자 기본 이름과 겹치지 않게 Ts)
    end
    properties (Access = protected)
        P; St; i; ctx
    end
    methods (Access = protected)
        function setupImpl(obj, varargin)
            obj.ctx = pc_sl_ctx(obj.CtxVar); obj.P = obj.ctx.P; obj.i = 0; obj.St = initStage(obj);
        end
        function resetImpl(obj)
            obj.i = 0; obj.St = initStage(obj);
        end
        function St = initStage(~)
            St = [];
        end
        function L = stageLog(~, L)
            % 서브클래스가 releaseImpl 기록(base 작업공간 pc_sl_logs)에 넣을 항목을 채운다
        end
        function releaseImpl(obj)
            if isempty(obj.St), return; end
            try, L = evalin('base', 'pc_sl_logs'); catch, L = struct(); end
            L = stageLog(obj, L);
            assignin('base', 'pc_sl_logs', L);
        end
        function varargout = isInputDirectFeedthroughImpl(obj, varargin)
            varargout = num2cell(true(1, getNumInputs(obj)));
        end
        function varargout = getOutputDataTypeImpl(obj)
            varargout = repmat({'double'}, 1, getNumOutputs(obj));
        end
        function varargout = isOutputComplexImpl(obj)
            varargout = repmat({false}, 1, getNumOutputs(obj));
        end
        function varargout = isOutputFixedSizeImpl(obj)
            varargout = repmat({true}, 1, getNumOutputs(obj));
        end
        function sts = getSampleTimeImpl(obj)
            sts = createSampleTime(obj, 'Type', 'Discrete', 'SampleTime', obj.Ts);
        end
    end
end
