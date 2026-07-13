import {motion} from 'motion/react';
import {
  Activity,
  CircleDotDashed,
  FileCheck2,
  Layers3,
  Network,
  ScanLine,
  SplitSquareVertical,
} from 'lucide-react';
import {useEffect, useState} from 'react';
import type {HealthStatus} from '../types';

const PIPELINE_OPERATIONS = [
  {label: 'Input validation and tiling', icon: Layers3},
  {label: 'Attn-Dist-Net inference', icon: Network},
  {label: 'Mask and distance decoding', icon: SplitSquareVertical},
  {label: 'Watershed reconstruction', icon: ScanLine},
  {label: 'Morphology and export artifacts', icon: FileCheck2},
] as const;

interface ProcessingViewProps {
  caseId: string;
  fileName: string;
  imageUrl: string;
  health: HealthStatus | null;
}

export function ProcessingView({caseId, fileName, imageUrl, health}: ProcessingViewProps) {
  const [elapsedTenths, setElapsedTenths] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsedTenths((value) => value + 1), 100);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <motion.div initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} className="absolute inset-0 flex items-center justify-center overflow-y-auto bg-[#090a0c] p-5 lg:p-8">
      <div className="flex w-full max-w-6xl flex-col items-center justify-center gap-10 lg:flex-row lg:gap-20">
        <section className="w-full max-w-[420px] shrink-0 rounded-[32px] border border-white/10 bg-[#0c0d10] p-7 shadow-2xl">
          <header className="mb-6 flex items-end justify-between gap-4">
            <div><div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase text-zinc-500"><Layers3 className="h-3.5 w-3.5 text-blue-500" />Spatial patch analysis</div><div className="font-mono text-3xl font-bold text-white">{(elapsedTenths / 10).toFixed(1)}s</div></div>
            <div className="text-right"><div className="text-[9px] font-bold uppercase text-zinc-600">Request state</div><div className="mt-1 flex items-center justify-end gap-2 text-[10px] font-mono text-blue-400"><span className="status-pulse h-2 w-2 rounded-full bg-blue-400" />Processing</div></div>
          </header>

          <div className="relative aspect-square overflow-hidden rounded-lg border border-white/10 bg-black">
            <img className="absolute inset-0 h-full w-full object-contain opacity-70" src={imageUrl} alt="Image being analyzed" />
            <div className="absolute inset-0 grid place-items-center bg-black/35"><div className="grid h-16 w-16 place-items-center rounded-full border border-blue-500/30 bg-black/70"><Activity className="status-pulse h-7 w-7 text-blue-400" /></div></div>
          </div>

          <footer className="mt-6 grid grid-cols-2 gap-4 border-t border-white/5 pt-5 font-mono">
            <div><span className="block text-[9px] uppercase text-zinc-600">Analysis ID</span><strong className="mt-1 block truncate text-xs text-zinc-300">{caseId}</strong></div>
            <div className="text-right"><span className="block text-[9px] uppercase text-zinc-600">Runtime</span><strong className="mt-1 block text-xs text-emerald-400">{health?.device ?? 'Local'}</strong></div>
            <div className="col-span-2 min-w-0"><span className="block text-[9px] uppercase text-zinc-600">Input</span><strong className="mt-1 block truncate text-xs text-zinc-400">{fileName}</strong></div>
          </footer>
        </section>

        <section className="w-full max-w-xl">
          <div className="mb-8 flex items-center justify-between gap-4"><h1 className="text-[10px] font-bold uppercase text-zinc-500">Attn-Dist-Net pipeline</h1><span className="rounded border border-white/10 px-2 py-1 font-mono text-[9px] uppercase text-zinc-600">Server-managed operation</span></div>
          <div className="space-y-6">
            {PIPELINE_OPERATIONS.map((step) => {
              const Icon = step.icon;
              return (
                <div key={step.label} className="flex items-center gap-5 border-l border-white/10 py-1 pl-6">
                  <div className="grid h-12 w-12 shrink-0 place-items-center rounded-full border border-white/10 bg-white/[0.02] text-zinc-500"><Icon className="h-4 w-4" /></div>
                  <div><h2 className="text-lg font-bold text-zinc-300">{step.label}</h2><p className="mt-1 text-[10px] font-bold uppercase text-zinc-600">Executed within the active API request</p></div>
                </div>
              );
            })}
          </div>
          <div className="mt-8 flex items-start gap-3 rounded-md border border-white/8 bg-[#121317] p-4 text-xs leading-5 text-zinc-500"><CircleDotDashed className="mt-0.5 h-4 w-4 shrink-0 text-blue-400" /><p>The API reports request completion as one atomic response. Elapsed time is measured locally; no stage progress or result values are estimated.</p></div>
        </section>
      </div>
    </motion.div>
  );
}
