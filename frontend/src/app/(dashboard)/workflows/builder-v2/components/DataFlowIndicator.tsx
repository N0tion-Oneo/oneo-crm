/**
 * DataFlowIndicator Component
 * Visual indicator showing data flow between input, config, and output panels
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { ArrowRight, Zap, Activity } from 'lucide-react';

interface DataFlowIndicatorProps {
  active?: boolean;
  direction?: 'horizontal' | 'vertical';
  label?: string;
  className?: string;
  animate?: boolean;
}

export function DataFlowIndicator({
  active = false,
  direction = 'horizontal',
  label,
  className,
  animate = true
}: DataFlowIndicatorProps) {
  const isHorizontal = direction === 'horizontal';

  return (
    <div
      className={cn(
        'relative flex items-center justify-center',
        isHorizontal ? 'w-12 h-full' : 'w-full h-12',
        className
      )}
    >
      {/* Flow line */}
      <div
        className={cn(
          'absolute bg-gradient-to-r from-blue-200 via-purple-200 to-green-200',
          isHorizontal ? 'w-1 h-full left-1/2 -translate-x-1/2' : 'h-1 w-full top-1/2 -translate-y-1/2',
          active && 'from-blue-400 via-purple-400 to-green-400'
        )}
      >
        {/* Animated pulse effect */}
        {active && animate && (
          <div
            className={cn(
              'absolute bg-white rounded-full opacity-75',
              isHorizontal ? 'w-1 h-4' : 'w-4 h-1',
              'animate-pulse-flow'
            )}
            style={{
              animation: 'flowPulse 2s linear infinite'
            }}
          />
        )}
      </div>

      {/* Center icon */}
      <div
        className={cn(
          'relative z-10 rounded-full bg-background border-2 p-1.5',
          'transition-all duration-300',
          active
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-950 scale-110'
            : 'border-gray-300 dark:border-gray-600'
        )}
      >
        {active ? (
          <Activity className="h-4 w-4 text-blue-500 animate-pulse" />
        ) : (
          <ArrowRight
            className={cn(
              'h-4 w-4 text-gray-400',
              !isHorizontal && 'rotate-90'
            )}
          />
        )}
      </div>

      {/* Label */}
      {label && (
        <div
          className={cn(
            'absolute text-xs text-muted-foreground whitespace-nowrap',
            isHorizontal ? 'top-full mt-2' : 'left-full ml-2'
          )}
        >
          {label}
        </div>
      )}

      {/* Add CSS animation */}
      <style jsx>{`
        @keyframes flowPulse {
          0% {
            transform: ${isHorizontal ? 'translateY(-100%)' : 'translateX(-100%)'};
            opacity: 0;
          }
          20% {
            opacity: 1;
          }
          80% {
            opacity: 1;
          }
          100% {
            transform: ${isHorizontal ? 'translateY(100%)' : 'translateX(100%)'};
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}

/**
 * DataFlowPath Component
 * Shows a complete flow path with multiple stages
 */
export function DataFlowPath({
  stages = ['Input', 'Process', 'Output'],
  activeStage,
  className
}: {
  stages?: string[];
  activeStage?: number;
  className?: string;
}) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      {stages.map((stage, index) => (
        <React.Fragment key={stage}>
          <div
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium',
              'transition-all duration-300',
              activeStage === index
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 scale-105'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
            )}
          >
            <div
              className={cn(
                'w-2 h-2 rounded-full',
                activeStage === index
                  ? 'bg-blue-500 animate-pulse'
                  : 'bg-gray-400'
              )}
            />
            {stage}
          </div>
          {index < stages.length - 1 && (
            <ArrowRight
              className={cn(
                'h-4 w-4',
                activeStage === index
                  ? 'text-blue-500 animate-pulse'
                  : 'text-gray-400'
              )}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}