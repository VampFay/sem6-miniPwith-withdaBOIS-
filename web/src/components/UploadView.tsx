import {motion} from 'motion/react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Cpu,
  Database,
  FileImage,
  FolderOpen,
  Gauge,
  RefreshCw,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import {useEffect, useMemo, useRef, useState, type CSSProperties} from 'react';
import type {AnalysisOptions, AnalysisRequest, HealthStatus} from '../types';
import {cn} from '../utils';

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
const SUPPORTED_IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/tiff']);
const DEFAULT_OPTIONS: AnalysisOptions = {
  useTta: true,
  maskThreshold: 0.5,
  peakThreshold: 0.35,
  minSize: 10,
};

function createAnalysisId(): string {
  const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
  return `ANALYSIS-${timestamp}`;
}

interface UploadViewProps {
  health: HealthStatus | null;
  healthError: string | null;
  analysisError: string | null;
  onAnalyze: (request: AnalysisRequest) => void;
  onRefreshHealth: () => void;
}

function RangeControl({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  const progress = ((value - min) / (max - min)) * 100;
  const style = {'--range-progress': `${progress}%`} as CSSProperties;

  return (
    <label className="block border-b border-white/5 py-3">
      <span className="mb-2 flex items-center justify-between gap-3 text-[11px] font-semibold text-zinc-400">
        {label}<output className="min-w-12 rounded border border-white/10 bg-black/30 px-2 py-1 text-center font-mono text-[10px] text-zinc-200">{value}</output>
      </span>
      <input className="range-control w-full" style={style} aria-label={label} type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

export function UploadView({health, healthError, analysisError, onAnalyze, onRefreshHealth}: UploadViewProps) {
  const [caseId, setCaseId] = useState(createAnalysisId);
  const [options, setOptions] = useState(DEFAULT_OPTIONS);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const previewUrl = useMemo(() => file ? URL.createObjectURL(file) : null, [file]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const selectFile = (candidate: File | undefined) => {
    if (!candidate) return;
    if (!SUPPORTED_IMAGE_TYPES.has(candidate.type)) {
      setFileError('Select a PNG, JPEG, or TIFF image.');
      return;
    }
    if (candidate.size > MAX_UPLOAD_BYTES) {
      setFileError('The selected image exceeds the 25 MB limit.');
      return;
    }
    setFile(candidate);
    setFileError(null);
  };

  const canAnalyze = Boolean(file && caseId.trim() && health?.ready);

  return (
    <motion.div
      initial={{opacity: 0, y: 8}}
      animate={{opacity: 1, y: 0}}
      exit={{opacity: 0}}
      className="absolute inset-0 flex flex-col gap-5 overflow-y-auto bg-[#090a0c] p-4 lg:flex-row lg:overflow-hidden lg:p-6"
    >
      <aside className="flex min-w-0 shrink-0 flex-col rounded-lg border border-white/8 bg-[#121317] p-5 shadow-2xl lg:w-[340px] lg:overflow-y-auto">
        <div className="mb-6 flex items-center justify-between">
          <div><h1 className="text-xl font-bold text-white">Configuration</h1><p className="mt-1 text-xs text-zinc-500">Analysis parameters</p></div>
          <div className="grid h-10 w-10 place-items-center rounded-full border border-white/10 bg-white/5"><Settings className="h-5 w-5 text-zinc-400" /></div>
        </div>

        <section>
          <div className="mb-4 flex items-center gap-2"><Database className="h-4 w-4 text-blue-400" /><h2 className="text-sm font-bold text-zinc-300">Research context</h2></div>
          <label className="block text-[10px] font-bold uppercase text-zinc-500">
            Analysis ID
            <input className="mt-2 min-w-0 w-full rounded-md border border-white/10 bg-black/40 px-4 py-3 font-mono text-sm text-zinc-200 outline-none focus:border-blue-500/60" value={caseId} maxLength={64} onChange={(event) => setCaseId(event.target.value)} />
          </label>
        </section>

        <div className="my-6 h-px bg-white/5" />

        <section>
          <div className="mb-2 flex items-center gap-2"><SlidersHorizontal className="h-4 w-4 text-blue-400" /><h2 className="text-sm font-bold text-zinc-300">Inference controls</h2></div>
          <RangeControl label="Foreground threshold" value={options.maskThreshold} min={0.1} max={0.9} step={0.05} onChange={(value) => setOptions({...options, maskThreshold: value})} />
          <RangeControl label="Watershed peak threshold" value={options.peakThreshold} min={0.1} max={0.9} step={0.05} onChange={(value) => setOptions({...options, peakThreshold: value})} />
          <RangeControl label="Minimum nucleus area" value={options.minSize} min={1} max={100} step={1} onChange={(value) => setOptions({...options, minSize: value})} />
          <label className="mt-4 flex items-center justify-between gap-4 rounded-md border border-white/8 bg-black/20 p-3">
            <span><strong className="block text-xs text-zinc-300">Test-time augmentation</strong><small className="mt-1 block text-[10px] text-zinc-500">Four-view mask consensus</small></span>
            <input className="h-4 w-4 accent-blue-500" type="checkbox" checked={options.useTta} onChange={(event) => setOptions({...options, useTta: event.target.checked})} />
          </label>
        </section>
      </aside>

      <section className="relative flex min-h-[640px] min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-white/8 bg-[#121317] shadow-2xl lg:min-h-0">
        <div className="pointer-events-none absolute inset-0 opacity-[0.035]" style={{backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)', backgroundSize: '32px 32px'}} />
        <div
          className={cn('relative z-10 flex flex-1 items-center justify-center p-6 transition-colors lg:p-12', isDragging && 'bg-blue-500/10')}
          onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => { event.preventDefault(); setIsDragging(false); selectFile(event.dataTransfer.files[0]); }}
        >
          <input ref={inputRef} className="hidden" type="file" accept="image/png,image/jpeg,image/tiff" onChange={(event) => selectFile(event.target.files?.[0])} />
          <div className="flex w-full max-w-lg flex-col items-center">
            {file && previewUrl ? (
              <div className="mb-6 w-full max-w-[360px]">
                <div className="relative aspect-square overflow-hidden rounded-lg border border-white/15 bg-black/50">
                  <img className="h-full w-full object-contain" src={previewUrl} alt="Selected specimen preview" />
                  <button className="absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full border border-white/10 bg-black/80 text-white hover:bg-black" type="button" title="Remove image" onClick={() => setFile(null)}><X className="h-4 w-4" /></button>
                </div>
                <div className="mt-3 flex min-w-0 items-center gap-3 rounded-md border border-white/10 bg-black/30 p-3">
                  <FileImage className="h-5 w-5 shrink-0 text-blue-400" />
                  <span className="min-w-0 flex-1"><strong className="block truncate text-xs text-zinc-200">{file.name}</strong><small className="text-[10px] text-zinc-500">{(file.size / 1024).toFixed(1)} KB</small></span>
                  <button className="text-[10px] font-bold uppercase text-blue-400 hover:text-blue-300" type="button" onClick={() => inputRef.current?.click()}>Replace</button>
                </div>
              </div>
            ) : (
              <>
                <button className="mb-7 grid h-24 w-24 place-items-center rounded-full border border-blue-500/30 bg-blue-600/10 text-blue-400 shadow-[0_0_40px_rgba(59,130,246,0.12)] hover:bg-blue-600/15" type="button" title="Select pathology image" onClick={() => inputRef.current?.click()}><FolderOpen className="h-10 w-10" /></button>
                <h2 className="text-center text-3xl font-bold text-white">Load image patch</h2>
                <button className="mt-3 text-center font-mono text-sm leading-6 text-zinc-400 hover:text-white" type="button" onClick={() => inputRef.current?.click()}>Click or drag and drop a pathology image.<br /><span className="text-blue-400">Supported: PNG, JPEG, TIFF</span></button>
              </>
            )}

            {(fileError || analysisError) && <div className="mt-5 flex max-w-md items-start gap-2 rounded-md border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-300"><AlertTriangle className="h-4 w-4 shrink-0" />{fileError ?? analysisError}</div>}
            {healthError && <div className="mt-5 flex max-w-md items-center gap-2 rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-200"><AlertTriangle className="h-4 w-4" />Inference API unavailable.<button type="button" className="ml-auto" title="Retry API connection" onClick={onRefreshHealth}><RefreshCw className="h-4 w-4" /></button></div>}
            {health && !health.ready && <div className="mt-5 max-w-md rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-center font-mono text-[10px] text-amber-200">{health.status === 'invalid_checkpoint' ? 'Installed checkpoint failed validation. Replace it with a version-2 inference artifact.' : 'Install outputs_v2/checkpoints/best_iou.pt to enable inference.'}</div>}

            <motion.button whileHover={canAnalyze ? {scale: 1.02} : undefined} whileTap={canAnalyze ? {scale: 0.98} : undefined} className={cn('mt-8 flex min-h-12 items-center gap-3 rounded-full px-8 text-sm font-bold uppercase', canAnalyze ? 'bg-white text-black hover:bg-zinc-100' : 'cursor-not-allowed border border-white/5 bg-white/10 text-zinc-600')} type="button" disabled={!canAnalyze} onClick={() => file && caseId.trim() && onAnalyze({caseId: caseId.trim(), file, options})}><span>{health?.ready ? 'Initialize pipeline' : 'Checkpoint required'}</span><ArrowRight className="h-4 w-4" /></motion.button>
          </div>
        </div>

        <footer className="relative z-10 m-4 flex flex-col gap-4 rounded-lg border border-white/10 bg-black/40 p-4 sm:flex-row sm:items-center sm:justify-between lg:m-6">
          <div className="flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-full border border-emerald-500/20 bg-emerald-500/10"><ShieldCheck className="h-5 w-5 text-emerald-400" /></div><div><strong className="text-sm text-white">Local research processing</strong><p className="mt-1 text-[10px] font-mono uppercase text-emerald-400/80">Requests stay on the configured local API</p></div></div>
          <div className="text-left sm:text-right"><div className="text-[10px] font-bold uppercase text-zinc-500">Runtime target</div><div className="mt-1 flex items-center gap-2 text-xs font-mono text-zinc-300 sm:justify-end">{health?.device === 'MPS' ? <Activity className="h-3.5 w-3.5 text-emerald-400" /> : <Cpu className="h-3.5 w-3.5 text-emerald-400" />}<span>{health?.device ?? 'Checking'}</span><span className="text-zinc-600">|</span><Gauge className="h-3.5 w-3.5 text-blue-400" /><span>{health?.checkpoint ?? 'No checkpoint'}</span></div></div>
        </footer>
      </section>
    </motion.div>
  );
}
