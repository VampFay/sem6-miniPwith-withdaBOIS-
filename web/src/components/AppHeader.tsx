import {
  Activity,
  BookOpen,
  Cpu,
  FilePlus2,
  Github,
  ShieldCheck,
} from 'lucide-react';
import type {AppState, HealthStatus} from '../types';

interface AppHeaderProps {
  appState: AppState;
  health: HealthStatus | null;
  onNewCase: () => void;
}

export function AppHeader({appState, health, onNewCase}: AppHeaderProps) {
  return (
    <header className="z-50 flex h-12 w-full shrink-0 items-center justify-between border-b border-white/10 bg-[#121317] px-4">
      <div className="flex min-w-0 items-center gap-6">
        <div className="flex items-center gap-2 text-white">
          <Activity className="h-5 w-5 text-blue-500" />
          <span className="text-sm font-bold">ATTN<span className="text-zinc-400">DIST</span></span>
        </div>
        <nav className="hidden items-center gap-5 md:flex" aria-label="Project resources">
          <a className="text-[10px] font-bold uppercase text-zinc-400 hover:text-white" href="https://github.com/VampFay/sem6-miniPwith-withdaBOIS-" target="_blank" rel="noreferrer"><Github className="mr-1.5 inline h-3.5 w-3.5" />Project</a>
          <a className="text-[10px] font-bold uppercase text-zinc-400 hover:text-white" href="https://github.com/VampFay/sem6-miniPwith-withdaBOIS-/blob/main/docs/METHODOLOGY.md" target="_blank" rel="noreferrer"><BookOpen className="mr-1.5 inline h-3.5 w-3.5" />Methodology</a>
          {appState === 'results' && <button className="text-[10px] font-bold uppercase text-zinc-400 hover:text-white" type="button" onClick={onNewCase}><FilePlus2 className="mr-1.5 inline h-3.5 w-3.5" />New analysis</button>}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 border-r border-white/10 pr-3 sm:flex">
          <span className={`h-2 w-2 rounded-full ${health ? health.ready ? 'bg-emerald-400' : health.status === 'invalid_checkpoint' ? 'bg-red-400' : 'bg-amber-400' : 'status-pulse bg-zinc-500'}`} />
          <span className="text-[10px] font-bold uppercase text-zinc-400">{health ? health.ready ? 'Model validated' : health.status === 'invalid_checkpoint' ? 'Invalid checkpoint' : 'Setup required' : 'Checking runtime'}</span>
        </div>
        <div className="flex items-center gap-2 text-zinc-300">
          {health?.device ? <Cpu className="h-4 w-4 text-blue-400" /> : <ShieldCheck className="h-4 w-4 text-zinc-500" />}
          <span className="hidden text-[10px] font-bold uppercase sm:block">Research workspace</span>
        </div>
      </div>
    </header>
  );
}
