import { useState } from 'react';
import { RotateCcw, ChevronDown } from 'lucide-react';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import { Button } from '../components/ui/button';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_COLORS = {
  pending: 'text-[#FFD60A]',
  running: 'text-[#007AFF]',
  completed: 'text-[#34C759]',
  failed: 'text-[#FF3B30]',
  retrying: 'text-[#FFD60A]',
};

const STATUS_DOTS = {
  pending: 'bg-[#FFD60A]',
  running: 'bg-[#007AFF] pulse-dot',
  completed: 'bg-[#34C759]',
  failed: 'bg-[#FF3B30]',
  retrying: 'bg-[#FFD60A] pulse-dot',
};

/**
 * Job table with dense rows, status filtering, and retry actions.
 * Uses JetBrains Mono for data columns per design spec.
 */
export function JobTable({ jobs, onRefresh, flashIds }) {
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  const filtered = jobs.filter(j => {
    if (statusFilter !== 'all' && j.status !== statusFilter) return false;
    if (typeFilter !== 'all' && j.type !== typeFilter) return false;
    return true;
  });

  const retryJob = async (jobId) => {
    try {
      await fetch(`${API}/jobs/${jobId}/retry`, { method: 'POST' });
      onRefresh?.();
    } catch (e) {
      console.error('Retry failed:', e);
    }
  };

  const formatTime = (iso) => {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div data-testid="job-table-container" className="border border-border bg-[#121214] rounded-sm">
      {/* Filters */}
      <div className="flex items-center gap-3 p-4 border-b border-border">
        <span className="text-xs text-[#71717A] uppercase tracking-wider">Filter</span>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger data-testid="status-filter" className="w-[140px] h-8 text-xs bg-[#1A1A1E] border-border rounded-sm">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent className="bg-[#1A1A1E] border-border rounded-sm">
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="retrying">Retrying</SelectItem>
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger data-testid="type-filter" className="w-[140px] h-8 text-xs bg-[#1A1A1E] border-border rounded-sm">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent className="bg-[#1A1A1E] border-border rounded-sm">
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="compute">Compute</SelectItem>
            <SelectItem value="pipeline">Pipeline</SelectItem>
          </SelectContent>
        </Select>
        <span className="ml-auto text-xs font-mono-data text-[#71717A]">
          {filtered.length} jobs
        </span>
      </div>

      {/* Table */}
      <div className="max-h-[400px] overflow-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-xs text-[#71717A] uppercase tracking-wider w-[80px]">ID</TableHead>
              <TableHead className="text-xs text-[#71717A] uppercase tracking-wider">Name</TableHead>
              <TableHead className="text-xs text-[#71717A] uppercase tracking-wider w-[90px]">Type</TableHead>
              <TableHead className="text-xs text-[#71717A] uppercase tracking-wider w-[100px]">Status</TableHead>
              <TableHead className="text-xs text-[#71717A] uppercase tracking-wider w-[70px]">Retries</TableHead>
              <TableHead className="text-xs text-[#71717A] uppercase tracking-wider w-[80px]">Worker</TableHead>
              <TableHead className="text-xs text-[#71717A] uppercase tracking-wider w-[80px]">Time</TableHead>
              <TableHead className="text-xs text-[#71717A] uppercase tracking-wider w-[70px]">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-[#71717A] py-12 text-sm">
                  No jobs found. Create a job to get started.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((job) => (
                <TableRow
                  key={job.id}
                  data-testid={`job-row-${job.id}`}
                  className={`border-border hover:bg-[#1A1A1E]/50 ${flashIds?.has(job.id) ? 'ws-flash' : ''}`}
                >
                  <TableCell className="font-mono-data text-xs text-[#A1A1AA]">{job.id}</TableCell>
                  <TableCell className="font-mono-data text-xs text-white">{job.name}</TableCell>
                  <TableCell>
                    <span className={`font-mono-data text-xs px-1.5 py-0.5 border rounded-sm ${
                      job.type === 'compute'
                        ? 'border-[#007AFF]/30 text-[#007AFF] bg-[#007AFF]/5'
                        : 'border-[#A855F7]/30 text-[#A855F7] bg-[#A855F7]/5'
                    }`}>
                      {job.type}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className={`flex items-center gap-1.5 font-mono-data text-xs ${STATUS_COLORS[job.status]}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOTS[job.status]}`} />
                      {job.status}
                      {job.pipeline_stage && job.status === 'running' && (
                        <span className="text-[#71717A]">/{job.pipeline_stage}</span>
                      )}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono-data text-xs text-[#A1A1AA]">
                    {job.retries}/{job.max_retries}
                  </TableCell>
                  <TableCell className="font-mono-data text-xs text-[#71717A]">
                    {job.worker_id || '—'}
                  </TableCell>
                  <TableCell className="font-mono-data text-xs text-[#A1A1AA]">
                    {job.execution_time ? `${job.execution_time}s` : '—'}
                  </TableCell>
                  <TableCell>
                    {job.status === 'failed' && (
                      <Button
                        data-testid={`retry-job-${job.id}`}
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 text-[#FFD60A] hover:text-[#FFD60A] hover:bg-[#FFD60A]/10"
                        onClick={() => retryJob(job.id)}
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
