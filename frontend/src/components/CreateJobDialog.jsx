import { useState } from 'react';
import { Plus, Layers, Cpu } from 'lucide-react';
import { Button } from '../components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Dialog for creating new jobs. Supports both compute and pipeline types.
 */
export function CreateJobDialog({ onCreated }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [type, setType] = useState('compute');
  const [maxRetries, setMaxRetries] = useState('3');
  const [loading, setLoading] = useState(false);

  const createJob = async () => {
    if (!name.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          type,
          max_retries: parseInt(maxRetries),
        }),
      });
      if (res.ok) {
        setOpen(false);
        setName('');
        onCreated?.();
      }
    } catch (e) {
      console.error('Failed to create job:', e);
    } finally {
      setLoading(false);
    }
  };

  const createBatch = async (count) => {
    setLoading(true);
    try {
      await fetch(`${API}/jobs/batch?count=${count}`, { method: 'POST' });
      setOpen(false);
      onCreated?.();
    } catch (e) {
      console.error('Batch create failed:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          data-testid="create-job-button"
          className="bg-[#007AFF] text-white hover:bg-[#3395FF] rounded-sm h-8 text-xs font-medium px-3"
        >
          <Plus className="w-3.5 h-3.5 mr-1.5" />
          New Job
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#121214] border-border rounded-sm sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle className="font-heading text-lg text-white">Create Job</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <div className="space-y-2">
            <Label className="text-xs text-[#A1A1AA] uppercase tracking-wider">Job Name</Label>
            <Input
              data-testid="job-name-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. particle-sim-001"
              className="bg-[#1A1A1E] border-border text-white font-mono-data text-sm rounded-sm h-9"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs text-[#A1A1AA] uppercase tracking-wider">Job Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger data-testid="job-type-select" className="bg-[#1A1A1E] border-border text-white rounded-sm h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1A1A1E] border-border rounded-sm">
                <SelectItem value="compute">
                  <span className="flex items-center gap-2">
                    <Cpu className="w-3.5 h-3.5 text-[#007AFF]" /> Compute
                  </span>
                </SelectItem>
                <SelectItem value="pipeline">
                  <span className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-[#A855F7]" /> Pipeline
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-xs text-[#A1A1AA] uppercase tracking-wider">Max Retries</Label>
            <Input
              data-testid="max-retries-input"
              type="number"
              value={maxRetries}
              onChange={(e) => setMaxRetries(e.target.value)}
              min="0"
              max="10"
              className="bg-[#1A1A1E] border-border text-white font-mono-data text-sm rounded-sm h-9"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              data-testid="submit-create-job"
              onClick={createJob}
              disabled={loading || !name.trim()}
              className="flex-1 bg-[#007AFF] text-white hover:bg-[#3395FF] rounded-sm h-9 text-xs"
            >
              {loading ? 'Creating...' : 'Create Job'}
            </Button>
          </div>

          <div className="border-t border-border pt-3">
            <Label className="text-xs text-[#71717A] uppercase tracking-wider mb-2 block">Quick Batch</Label>
            <div className="flex gap-2">
              {[5, 10, 20].map(n => (
                <Button
                  key={n}
                  data-testid={`batch-create-${n}`}
                  variant="outline"
                  size="sm"
                  onClick={() => createBatch(n)}
                  disabled={loading}
                  className="flex-1 text-xs border-border text-[#A1A1AA] hover:text-white hover:bg-[#1A1A1E] rounded-sm h-8"
                >
                  {n} Jobs
                </Button>
              ))}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
