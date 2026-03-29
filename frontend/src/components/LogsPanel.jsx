import { useRef, useEffect, useState } from 'react';
import { Terminal, Pause, Play } from 'lucide-react';
import { Button } from '../components/ui/button';

/**
 * Live logs terminal panel with auto-scroll and level-based coloring.
 * Renders in JetBrains Mono with a deep black background.
 */
export function LogsPanel({ logs }) {
  const bottomRef = useRef(null);
  const containerRef = useRef(null);
  const [autoscroll, setAutoscroll] = useState(true);

  useEffect(() => {
    if (autoscroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoscroll]);

  const getLevelClass = (level) => {
    switch (level?.toUpperCase()) {
      case 'ERROR': return 'log-error';
      case 'WARNING': return 'log-warning';
      case 'INFO': return 'log-info';
      default: return 'text-[#71717A]';
    }
  };

  const getLevelBadge = (level) => {
    const upper = level?.toUpperCase() || 'INFO';
    const colors = {
      ERROR: 'text-[#FF3B30] bg-[#FF3B30]/10',
      WARNING: 'text-[#FFD60A] bg-[#FFD60A]/10',
      INFO: 'text-[#007AFF] bg-[#007AFF]/10',
    };
    return colors[upper] || colors.INFO;
  };

  const formatTimestamp = (ts) => {
    if (!ts) return '00:00:00';
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour12: false });
  };

  return (
    <div data-testid="logs-panel" className="border border-border bg-[#121214] rounded-sm flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-[#007AFF]" strokeWidth={1.5} />
          <span className="text-xs text-[#71717A] uppercase tracking-wider">Live Logs</span>
          <span className="font-mono-data text-xs text-[#71717A]">({logs.length})</span>
        </div>
        <Button
          data-testid="toggle-autoscroll"
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-xs text-[#71717A] hover:text-white hover:bg-[#1A1A1E]"
          onClick={() => setAutoscroll(!autoscroll)}
        >
          {autoscroll ? <Pause className="w-3 h-3 mr-1" /> : <Play className="w-3 h-3 mr-1" />}
          {autoscroll ? 'Pause' : 'Resume'}
        </Button>
      </div>

      {/* Log stream */}
      <div
        ref={containerRef}
        className="logs-terminal h-[300px] overflow-auto p-3 space-y-0.5"
      >
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-[#71717A] text-xs">
            Waiting for log events...
          </div>
        ) : (
          logs.map((log, i) => (
            <div
              key={i}
              data-testid={`log-entry-${i}`}
              className={`flex gap-2 text-xs leading-relaxed ${getLevelClass(log.level)}`}
            >
              <span className="text-[#3f3f46] shrink-0">{formatTimestamp(log.timestamp)}</span>
              <span className={`px-1 rounded-sm shrink-0 ${getLevelBadge(log.level)}`}>
                {(log.level || 'INFO').padEnd(7)}
              </span>
              <span className="text-[#71717A] shrink-0">[{log.source}]</span>
              <span className="text-[#A1A1AA] break-all">{log.message}</span>
              {log.job_id && (
                <span className="text-[#3f3f46] shrink-0">#{log.job_id}</span>
              )}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
