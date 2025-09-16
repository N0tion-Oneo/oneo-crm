import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { RotateCw, ArrowRight, ArrowUpLeft, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface WorkflowLoopControllerData {
  label: string;
  loop_key?: string;
  loop_type?: 'conditional' | 'count_based' | 'time_based' | 'until_success';
  max_iterations?: number;
  current_iteration?: number;
  exit_conditions?: Array<any>;
  status?: 'idle' | 'looping' | 'completed' | 'failed';
  exit_reason?: string;
  nodeType?: string;
  config?: any;
}

const WorkflowLoopControllerNode = memo(({ data, selected }: NodeProps<WorkflowLoopControllerData>) => {
  const loopType = data.loop_type || 'conditional';
  const maxIterations = data.max_iterations || 10;
  const currentIteration = data.current_iteration || 0;
  const status = data.status || 'idle';
  const exitConditions = data.exit_conditions || [];

  // Calculate progress
  const progress = maxIterations > 0 ? (currentIteration / maxIterations) * 100 : 0;

  // Determine if we're at risk of infinite loop
  const isHighIteration = currentIteration > maxIterations * 0.8;

  return (
    <div
      className={cn(
        'workflow-loop-controller-node relative',
        'transition-all duration-200'
      )}
    >
      {/* Diamond Shape Container */}
      <div
        className={cn(
          'w-48 h-48 relative',
          'transform rotate-45',
          selected && 'scale-105'
        )}
      >
        {/* Diamond Background */}
        <div
          className={cn(
            'absolute inset-0 rounded-lg',
            'bg-gradient-to-br from-indigo-100 to-purple-100',
            'border-2',
            selected ? 'border-indigo-500 shadow-lg' : 'border-indigo-400',
            status === 'looping' && 'animate-pulse',
            isHighIteration && 'border-orange-400 bg-gradient-to-br from-orange-100 to-yellow-100'
          )}
        />

        {/* Content Container (rotated back) */}
        <div className="absolute inset-0 flex items-center justify-center -rotate-45">
          <div className="text-center p-4">
            {/* Icon */}
            <div className="flex justify-center mb-2">
              <div className={cn(
                "p-2 rounded-full",
                status === 'looping' ? 'bg-indigo-500 animate-spin-slow' : 'bg-indigo-400',
                isHighIteration && 'bg-orange-500'
              )}>
                {isHighIteration ? (
                  <AlertCircle className="w-5 h-5 text-white" />
                ) : (
                  <RotateCw className="w-5 h-5 text-white" />
                )}
              </div>
            </div>

            {/* Label */}
            <div className="font-semibold text-sm text-gray-800 mb-1">
              Loop Control
            </div>

            {/* Loop Type Badge */}
            <Badge
              variant="outline"
              className={cn(
                "text-xs mb-2",
                isHighIteration && "border-orange-400 text-orange-600"
              )}
            >
              {loopType.replace('_', ' ')}
            </Badge>

            {/* Iteration Counter */}
            {status === 'looping' && (
              <div className="text-xs text-gray-600">
                {currentIteration} / {maxIterations}
              </div>
            )}

            {/* Progress Bar */}
            {status === 'looping' && progress > 0 && (
              <div className="w-full mt-2">
                <div className="w-full bg-gray-200 rounded-full h-1">
                  <div
                    className={cn(
                      "h-1 rounded-full transition-all duration-300",
                      isHighIteration ? "bg-orange-500" : "bg-indigo-500"
                    )}
                    style={{ width: `${Math.min(progress, 100)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Exit Conditions Indicator */}
            {exitConditions.length > 0 && (
              <div className="text-xs text-gray-500 mt-1">
                {exitConditions.length} condition{exitConditions.length !== 1 ? 's' : ''}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 bg-indigo-500 border-2 border-white"
        style={{ top: '20px' }}
      />

      {/* Output Handles with Labels */}

      {/* Loop Back Handle (Left) */}
      <div className="absolute left-0 top-1/2 -translate-y-1/2">
        <Handle
          type="source"
          position={Position.Left}
          id="loop"
          className="w-3 h-3 bg-green-500 border-2 border-white"
          style={{ left: '20px' }}
        />
        <div className="absolute -left-12 top-1/2 -translate-y-1/2 pointer-events-none">
          <div className="flex items-center gap-1 bg-green-100 text-green-700 px-2 py-1 rounded text-xs whitespace-nowrap border border-green-300">
            <ArrowUpLeft className="w-3 h-3" />
            Loop
          </div>
        </div>
      </div>

      {/* Exit Handle (Bottom) */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2">
        <Handle
          type="source"
          position={Position.Bottom}
          id="exit"
          className="w-3 h-3 bg-blue-500 border-2 border-white"
          style={{ bottom: '20px' }}
        />
        <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 pointer-events-none">
          <div className="flex items-center gap-1 bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs whitespace-nowrap border border-blue-300">
            <ArrowRight className="w-3 h-3" />
            Exit
          </div>
        </div>
      </div>

      {/* Status Indicator */}
      {status !== 'idle' && (
        <div className="absolute -top-8 left-1/2 -translate-x-1/2">
          <Badge
            variant={status === 'completed' ? 'secondary' : status === 'failed' ? 'destructive' : 'default'}
            className="text-xs"
          >
            {status}
          </Badge>
        </div>
      )}

      {/* Warning for high iterations */}
      {isHighIteration && status === 'looping' && (
        <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 flex items-center gap-1 text-xs text-orange-600">
          <AlertCircle className="w-3 h-3" />
          <span>High iteration count</span>
        </div>
      )}
    </div>
  );
});

WorkflowLoopControllerNode.displayName = 'WorkflowLoopControllerNode';

export default WorkflowLoopControllerNode;