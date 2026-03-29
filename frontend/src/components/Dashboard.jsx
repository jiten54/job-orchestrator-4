import { useState, useEffect, useCallback, useRef } from 'react';
import { RefreshCw, Shield, Wifi, WifiOff, Server, RotateCcw } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Toaster, toast } from 'sonner';
import { MetricCards } from './MetricCards';
import { JobTable } from './JobTable';
import { LogsPanel } from './LogsPanel';
import { CreateJobDialog } from './CreateJobDialog';
import { useWebSocket } from '../hooks/useWebSocket';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DEFAULT_METRICS = {
  total_jobs: 0, pending: 0, running: 0, completed: 0, failed: 0,
  retrying: 0, success_rate: 0, failure_rate: 0, avg_execution_time: 0,
  total_retries: 0, worker_count: 0, uptime_seconds: 0,
};

/**
 * Main orchestrator dashboard. Combines metric cards, job table,
 * logs panel, and control actions with real-time WebSocket updates.
 */
export default function Dashboard() {
  const [metrics, setMetrics] = useState(DEFAULT_METRICS);
  const [jobs, setJobs] = useState([]);
  const [logs, setLogs] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [flashIds, setFlashIds] = useState(new Set());
  const flashTimeout = useRef(null);

  // Fetch all data
  const fetchData = useCallback(async () => {
    try {
      const [metricsRes, jobsRes, logsRes, healthRes] = await Promise.all([
        fetch(`${API}/metrics`),
        fetch(`${API}/jobs`),
        fetch(`${API}/logs?limit=200`),
        fetch(`${API}/health`),
      ]);
      const [m, j, l, h] = await Promise.all([
        metricsRes.json(), jobsRes.json(), logsRes.json(), healthRes.json(),
      ]);
      setMetrics(m);
      setJobs(j);
      setLogs(l);
      setHealth(h);
    } catch (e) {
      console.error('Fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + periodic polling as fallback
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // WebSocket handler for real-time updates
  const handleWSMessage = useCallback((msg) => {
    if (!msg?.event) return;

    switch (msg.event) {
      case 'job_created':
      case 'job_updated':
      case 'job_retrying': {
        const jobData = msg.data;
        setJobs(prev => {
          const idx = prev.findIndex(j => j.id === jobData.id);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = jobData;
            return updated;
          }
          return [jobData, ...prev];
        });
        // Flash the updated row
        setFlashIds(prev => new Set([...prev, jobData.id]));
        clearTimeout(flashTimeout.current);
        flashTimeout.current = setTimeout(() => setFlashIds(new Set()), 1200);

        // Show toast for state transitions
        if (msg.event === 'job_updated') {
          if (jobData.status === 'completed') {
            toast.success(`Job ${jobData.id} completed`, {
              description: `${jobData.name} | ${jobData.execution_time}s`,
            });
          } else if (jobData.status === 'failed') {
            toast.error(`Job ${jobData.id} failed`, {
              description: jobData.error_message || 'Unknown error',
            });
          }
        }
        // Refresh metrics
        fetch(`${API}/metrics`).then(r => r.json()).then(setMetrics).catch(() => {});
        break;
      }
      case 'log': {
        setLogs(prev => [...prev.slice(-499), msg.data]);
        break;
      }
      case 'bulk_retry': {
        toast.info(`Recovery: ${msg.data.count} jobs re-enqueued`);
        fetchData();
        break;
      }
      default:
        break;
    }
  }, [fetchData]);

  const { connected } = useWebSocket(handleWSMessage);

  // Actions
  const retryAllFailed = async () => {
    try {
      const res = await fetch(`${API}/jobs/retry-all`, { method: 'POST' });
      const data = await res.json();
      toast.info(`Retried ${data.retried} failed jobs`);
      fetchData();
    } catch (e) {
      toast.error('Retry all failed');
    }
  };

  const triggerRecovery = async () => {
    try {
      const res = await fetch(`${API}/recovery/auto`, { method: 'POST' });
      const data = await res.json();
      toast.success(`Recovery: ${data.reset_jobs} reset, ${data.requeued_jobs} requeued`);
      fetchData();
    } catch (e) {
      toast.error('Recovery failed');
    }
  };

  const formatUptime = (seconds) => {
    if (!seconds) return '0s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  return (
    <div data-testid="dashboard" className="min-h-screen bg-[#09090B]">
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          className: 'border border-border rounded-sm bg-[#121214] text-white',
        }}
      />

      {/* Header */}
      <header data-testid="dashboard-header" className="border-b border-border bg-[#0C0C0E] relative overflow-hidden">
        <div className="relative z-10 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Server className="w-5 h-5 text-[#007AFF]" strokeWidth={1.5} />
              <h1 className="font-heading text-lg font-bold text-white tracking-tight">
                CERN-WFO
              </h1>
            </div>
            <div className="h-4 w-px bg-border" />
            <span className="text-xs text-[#71717A] font-mono-data">
              v1.0.0
            </span>
            <div className="h-4 w-px bg-border" />
            <div className="flex items-center gap-1.5">
              {connected ? (
                <Wifi className="w-3.5 h-3.5 text-[#34C759]" strokeWidth={2} />
              ) : (
                <WifiOff className="w-3.5 h-3.5 text-[#FF3B30]" strokeWidth={2} />
              )}
              <span data-testid="ws-status" className={`text-xs font-mono-data ${connected ? 'text-[#34C759]' : 'text-[#FF3B30]'}`}>
                {connected ? 'LIVE' : 'DISCONNECTED'}
              </span>
            </div>
            {health && (
              <>
                <div className="h-4 w-px bg-border" />
                <span className="text-xs text-[#71717A] font-mono-data">
                  uptime: {formatUptime(health.uptime_seconds)}
                </span>
                <span className="text-xs text-[#71717A] font-mono-data">
                  workers: {metrics.worker_count}
                </span>
                <span className="text-xs text-[#71717A] font-mono-data">
                  queue: {health.queue_depth}
                </span>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            <CreateJobDialog onCreated={fetchData} />
            <Button
              data-testid="retry-all-button"
              variant="outline"
              size="sm"
              onClick={retryAllFailed}
              className="border-border text-[#FFD60A] hover:bg-[#FFD60A]/10 hover:text-[#FFD60A] rounded-sm h-8 text-xs"
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
              Retry Failed
            </Button>
            <Button
              data-testid="auto-recovery-button"
              variant="outline"
              size="sm"
              onClick={triggerRecovery}
              className="border-border text-[#34C759] hover:bg-[#34C759]/10 hover:text-[#34C759] rounded-sm h-8 text-xs"
            >
              <Shield className="w-3.5 h-3.5 mr-1.5" />
              Auto Recovery
            </Button>
            <Button
              data-testid="refresh-button"
              variant="ghost"
              size="sm"
              onClick={fetchData}
              className="text-[#71717A] hover:text-white hover:bg-[#1A1A1E] rounded-sm h-8 w-8 p-0"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="p-6 space-y-4 max-w-[1600px] mx-auto">
        {loading ? (
          <div data-testid="loading-state" className="flex items-center justify-center h-64 text-[#71717A] text-sm">
            Initializing orchestrator...
          </div>
        ) : (
          <>
            {/* Metric cards */}
            <MetricCards metrics={metrics} />

            {/* Job table + Logs in grid layout */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
              <div className="lg:col-span-3">
                <JobTable jobs={jobs} onRefresh={fetchData} flashIds={flashIds} />
              </div>
              <div className="lg:col-span-2">
                <LogsPanel logs={logs} />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
