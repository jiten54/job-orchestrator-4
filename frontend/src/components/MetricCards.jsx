import { Activity, CheckCircle, XCircle, Clock, Zap, Timer, RotateCcw, Server } from 'lucide-react';

/**
 * Dashboard metric cards - KPI overview for the orchestrator.
 * Uses border-l-2 status indicators per design guidelines.
 */
export function MetricCards({ metrics }) {
  const cards = [
    {
      label: 'Total Jobs',
      value: metrics.total_jobs,
      icon: Activity,
      borderColor: 'border-l-[#007AFF]',
      textColor: 'text-[#007AFF]',
    },
    {
      label: 'Running',
      value: metrics.running,
      icon: Zap,
      borderColor: 'border-l-[#007AFF]',
      textColor: 'text-[#007AFF]',
    },
    {
      label: 'Completed',
      value: metrics.completed,
      icon: CheckCircle,
      borderColor: 'border-l-[#34C759]',
      textColor: 'text-[#34C759]',
    },
    {
      label: 'Failed',
      value: metrics.failed,
      icon: XCircle,
      borderColor: 'border-l-[#FF3B30]',
      textColor: 'text-[#FF3B30]',
    },
    {
      label: 'Pending',
      value: metrics.pending,
      icon: Clock,
      borderColor: 'border-l-[#FFD60A]',
      textColor: 'text-[#FFD60A]',
    },
    {
      label: 'Success Rate',
      value: `${metrics.success_rate}%`,
      icon: CheckCircle,
      borderColor: 'border-l-[#34C759]',
      textColor: 'text-[#34C759]',
    },
    {
      label: 'Avg Exec Time',
      value: `${metrics.avg_execution_time}s`,
      icon: Timer,
      borderColor: 'border-l-[#A1A1AA]',
      textColor: 'text-[#A1A1AA]',
    },
    {
      label: 'Total Retries',
      value: metrics.total_retries,
      icon: RotateCcw,
      borderColor: 'border-l-[#FFD60A]',
      textColor: 'text-[#FFD60A]',
    },
  ];

  return (
    <div data-testid="metric-cards" className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map((card, i) => (
        <div
          key={card.label}
          data-testid={`metric-card-${card.label.toLowerCase().replace(/\s+/g, '-')}`}
          className={`border border-border ${card.borderColor} border-l-2 bg-[#121214] p-4 rounded-sm animate-fade-in`}
          style={{ animationDelay: `${i * 50}ms` }}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-[#71717A] uppercase tracking-wider">{card.label}</span>
            <card.icon className={`w-4 h-4 ${card.textColor}`} strokeWidth={1.5} />
          </div>
          <div className={`font-mono-data text-2xl font-semibold ${card.textColor}`}>
            {card.value}
          </div>
        </div>
      ))}
    </div>
  );
}
