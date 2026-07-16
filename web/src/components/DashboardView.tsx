import {motion} from 'motion/react';
import {
  Activity,
  Download,
  Eye,
  FileImage,
  FileText,
  Focus,
  Gauge,
  Image as ImageIcon,
  Layers3,
  Maximize,
  Minus,
  Plus,
  RotateCcw,
  ScanSearch,
  Settings,
  TableProperties,
  Target,
} from 'lucide-react';
import {useMemo, useState} from 'react';
import type {AnalysisResult, HealthStatus, ResultView} from '../types';
import {cn} from '../utils';

interface DashboardViewProps {
  result: AnalysisResult;
  sourceUrl: string;
  caseId: string;
  fileName: string;
  health: HealthStatus | null;
  onReset: () => void;
}

const BASE_VIEWS: Array<{id: ResultView; label: string; icon: typeof Eye}> = [
  {id: 'source', label: 'Source', icon: FileImage},
  {id: 'overlay', label: 'Overlay', icon: Eye},
  {id: 'instances', label: 'Instances', icon: Layers3},
  {id: 'foreground_score', label: 'Foreground score', icon: ScanSearch},
  {id: 'distance', label: 'Distance', icon: Target},
];

function dataUrl(base64: string): string {
  return `data:image/png;base64,${base64}`;
}

function downloadBase64(base64: string, mime: string, filename: string): void {
  const link = document.createElement('a');
  link.href = `data:${mime};base64,${base64}`;
  link.download = filename;
  link.click();
}

function MetricBars({values, color}: {values: number[]; color: string}) {
  const sample = values.slice(0, 28);
  const max = Math.max(...sample, 1);
  return (
    <div className="absolute inset-x-1 bottom-5 top-1 flex items-end gap-px overflow-hidden">
      {sample.map((value, index) => <span key={index} className={cn('min-w-0 flex-1 opacity-80', color)} style={{height: `${Math.max(4, (value / max) * 100)}%`}} />)}
    </div>
  );
}

export function DashboardView({result, sourceUrl, caseId, fileName, health, onReset}: DashboardViewProps) {
  const [activeView, setActiveView] = useState<ResultView>('overlay');
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [dimensions, setDimensions] = useState('');

  const views = useMemo(
    () => result.images.tta_disagreement
      ? [...BASE_VIEWS, {id: 'tta_disagreement' as const, label: 'TTA disagreement', icon: Gauge}]
      : BASE_VIEWS,
    [result.images.tta_disagreement],
  );
  const encodedView = activeView === 'source' ? null : result.images[activeView];
  const viewSource = encodedView ? dataUrl(encodedView) : sourceUrl;
  const areas = useMemo(() => result.measurements.map((row) => row.area_px), [result.measurements]);
  const perimeters = useMemo(() => result.measurements.map((row) => row.perimeter_px), [result.measurements]);
  const eccentricities = useMemo(() => result.measurements.map((row) => row.eccentricity), [result.measurements]);
  const exportPrefix = caseId.replace(/[^a-z0-9_-]+/gi, '-').toLowerCase() || 'attn-dist';

  return (
    <motion.div initial={{opacity: 0}} animate={{opacity: 1}} className="h-full w-full overflow-y-auto bg-[#090a0c] text-zinc-300 xl:overflow-hidden">
      <div className="flex min-h-full flex-col xl:h-full xl:flex-row xl:overflow-hidden">
        <aside className="hidden w-[250px] shrink-0 flex-col border-r border-white/10 bg-[#121317] p-4 md:flex md:min-h-[620px] xl:overflow-y-auto">
          <section>
            <h2 className="mb-2 text-[10px] font-bold uppercase text-zinc-500">Analysis information</h2>
            <dl className="space-y-2 rounded-md border border-white/5 bg-[#1c1d22] p-3 font-mono text-[11px]">
              <div className="flex justify-between gap-3"><dt className="text-zinc-500">CASE ID</dt><dd className="truncate text-zinc-300">{caseId}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-zinc-500">DEVICE</dt><dd className="text-zinc-300">{health?.device ?? 'LOCAL'}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-zinc-500">FILE</dt><dd className="max-w-28 truncate border-b border-blue-500/40 text-zinc-300">{fileName}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-zinc-500">RELEASE</dt><dd className="max-w-28 truncate text-zinc-300">{result.provenance.release_id}</dd></div>
              <div className="flex justify-between gap-3"><dt className="text-zinc-500">MODE</dt><dd className="text-zinc-300">{result.provenance.operating_mode.toUpperCase()}</dd></div>
            </dl>
          </section>

          <section className="mt-5">
            <div className="mb-2 flex items-center justify-between"><h2 className="text-[10px] font-bold uppercase text-zinc-500">Layer toolbox</h2><Settings className="h-3 w-3 text-zinc-600" /></div>
            <div className="space-y-1.5">
              {views.map(({id, label, icon: Icon}) => (
                <button key={id} type="button" onClick={() => setActiveView(id)} className={cn('flex w-full items-center rounded border px-3 py-2 text-left transition-colors', activeView === id ? 'border-blue-500/50 bg-blue-600/20 text-blue-400' : 'border-white/10 bg-[#1c1d22] text-zinc-400 hover:bg-[#25262c] hover:text-white')}><Icon className="mr-3 h-4 w-4" /><span className="text-[11px] font-bold uppercase">{label}</span></button>
              ))}
            </div>
          </section>

          <section className="mt-5">
            <h2 className="mb-2 text-[10px] font-bold uppercase text-zinc-500">Completed pipeline</h2>
            <ol className="overflow-hidden rounded-md border border-white/5 bg-[#1c1d22] text-[10px] font-semibold uppercase text-zinc-400">
              {['Input validation', 'Mask and distance inference', 'Watershed reconstruction', 'Morphology and reports'].map((step, index) => <li key={step} className="border-b border-l-2 border-l-emerald-500/30 border-white/5 px-3 py-2.5 text-zinc-300">{index + 1}. {step}</li>)}
            </ol>
          </section>

          <section className="mt-5 rounded-md border border-white/5 bg-black/20 p-3 font-mono text-[9px] text-zinc-500">
            <div className="flex justify-between"><span>MASK THRESHOLD</span><strong className="text-zinc-300">{result.settings.mask_threshold}</strong></div>
            <div className="mt-2 flex justify-between"><span>PEAK THRESHOLD</span><strong className="text-zinc-300">{result.settings.peak_threshold}</strong></div>
            <div className="mt-2 flex justify-between"><span>MIN AREA</span><strong className="text-zinc-300">{result.settings.min_size} px^2</strong></div>
            <div className="mt-2 flex justify-between"><span>TTA</span><strong className="text-zinc-300">{result.settings.use_tta ? 'ON' : 'OFF'}</strong></div>
          </section>

          <button className="mt-auto rounded border border-white/10 py-2 text-[10px] font-semibold uppercase text-zinc-500 hover:text-white" type="button" onClick={onReset}>Close analysis</button>
        </aside>

        <main className="relative min-h-[66vh] flex-1 overflow-hidden bg-black xl:min-h-0">
          <div className="absolute left-4 top-4 z-20 flex items-center gap-1 rounded-md border border-white/10 bg-[#121317]/95 p-1 shadow-xl">
            <span className="flex items-center gap-2 px-2 font-mono text-[10px] font-bold uppercase text-zinc-300"><Activity className="h-3.5 w-3.5 text-blue-500" />{views.find((view) => view.id === activeView)?.label}</span>
            <span className="mx-1 h-5 w-px bg-white/10" />
            <button className="grid h-7 w-7 place-items-center rounded text-zinc-400 hover:bg-white/5 hover:text-white" type="button" title="Reset view" onClick={() => { setZoom(1); setRotation(0); }}><Focus className="h-4 w-4" /></button>
            <button className="grid h-7 w-7 place-items-center rounded text-zinc-400 hover:bg-white/5 hover:text-white" type="button" title="Rotate image" onClick={() => setRotation((value) => (value + 90) % 360)}><RotateCcw className="h-4 w-4" /></button>
          </div>

          <div className="absolute left-4 top-16 z-20 flex w-9 flex-col rounded-md border border-white/10 bg-[#121317]/95 p-1 shadow-xl">
            <button className="grid h-8 place-items-center text-zinc-400 hover:text-white" type="button" title="Zoom in" onClick={() => setZoom((value) => Math.min(3, value + 0.25))}><Plus className="h-4 w-4" /></button>
            <button className="grid h-8 place-items-center border-y border-white/10 text-zinc-400 hover:text-white" type="button" title="Zoom out" onClick={() => setZoom((value) => Math.max(0.5, value - 0.25))}><Minus className="h-4 w-4" /></button>
            <button className="grid h-8 place-items-center text-zinc-400 hover:text-white" type="button" title="Fit image" onClick={() => setZoom(1)}><Maximize className="h-4 w-4" /></button>
          </div>

          <div className="absolute right-4 top-4 z-20 w-40 rounded-md border border-white/10 bg-[#121317]/95 p-3 shadow-xl">
            <h2 className="border-b border-white/10 pb-2 text-[10px] font-bold uppercase text-zinc-300">Output layers</h2>
            <div className="mt-2 space-y-2 font-mono text-[9px] font-bold uppercase">
              <button className="flex w-full items-center text-blue-300" type="button" onClick={() => setActiveView('overlay')}><span className="mr-2 h-2 w-2 rounded-sm bg-blue-500" />Instance overlay</button>
              <button className="flex w-full items-center text-fuchsia-300" type="button" onClick={() => setActiveView('foreground_score')}><span className="mr-2 h-2 w-2 rounded-sm bg-fuchsia-500" />Foreground score</button>
              <button className="flex w-full items-center text-amber-200" type="button" onClick={() => setActiveView('distance')}><span className="mr-2 h-2 w-2 rounded-sm bg-amber-400" />Distance map</button>
              {result.images.tta_disagreement && <button className="flex w-full items-center text-emerald-200" type="button" onClick={() => setActiveView('tta_disagreement')}><span className="mr-2 h-2 w-2 rounded-sm bg-emerald-400" />TTA disagreement</button>}
            </div>
          </div>

          <div className="absolute inset-0 flex items-center justify-center overflow-hidden bg-[#0b0a0d]">
            <img
              className="h-full w-full object-contain transition-transform duration-200"
              style={{transform: `scale(${zoom}) rotate(${rotation}deg)`}}
              src={viewSource}
              alt={`${activeView} analysis view`}
              onLoad={(event) => setDimensions(`${event.currentTarget.naturalWidth} x ${event.currentTarget.naturalHeight} px`)}
            />
          </div>

          <div className="absolute bottom-4 left-4 z-20 flex items-center gap-3 rounded-md border border-white/10 bg-[#121317]/95 px-3 py-2 font-mono text-[9px] font-bold uppercase text-zinc-400"><span>Zoom {Math.round(zoom * 100)}%</span><span className="h-3 w-px bg-white/20" /><span>{dimensions}</span></div>

          <div className="absolute bottom-5 right-4 z-20 hidden overflow-hidden rounded-md border border-white/10 bg-[#121317]/95 shadow-xl sm:block">
            <div className="flex items-center justify-between border-b border-white/10 px-3 py-2 text-[9px] font-bold uppercase text-zinc-400"><span>Source reference</span><ImageIcon className="h-3 w-3" /></div>
            <div className="h-28 w-44 bg-black p-2"><img className="h-full w-full object-contain opacity-70" src={sourceUrl} alt="Source image reference" /></div>
          </div>
        </main>

        <aside className="flex w-full shrink-0 flex-col gap-4 border-l border-white/10 bg-[#0c0d10] p-4 xl:w-[380px] xl:overflow-y-auto">
          <section className="overflow-hidden rounded-md border border-white/10 bg-[#121317]">
            <header className="flex items-center justify-between border-b border-white/10 px-3 py-2"><h2 className="text-[10px] font-bold uppercase text-zinc-400">Segmentation results</h2><ScanSearch className="h-3.5 w-3.5 text-blue-400" /></header>
            <div className="bg-[#191a20] p-3">
              <div className="flex items-end justify-between"><div><span className="text-[9px] font-bold uppercase text-zinc-500">Segmented objects</span><strong className="mt-1 block font-mono text-3xl text-white">{result.metrics.nucleus_count.toLocaleString()}</strong></div><span className="font-mono text-[9px] uppercase text-zinc-600">Not diagnostic</span></div>
              <dl className="mt-4 grid grid-cols-2 gap-2">
                <div className="rounded border border-white/5 bg-black/20 p-2"><dt className="text-[9px] uppercase text-zinc-600">Mean area</dt><dd className="mt-1 font-mono text-xs text-zinc-300">{result.metrics.mean_area_px.toFixed(2)} px^2</dd></div>
                <div className="rounded border border-white/5 bg-black/20 p-2"><dt className="text-[9px] uppercase text-zinc-600">TTA disagreement</dt><dd className="mt-1 font-mono text-xs text-zinc-300">{result.metrics.mean_tta_disagreement === null ? 'Not calculated' : result.metrics.mean_tta_disagreement.toFixed(5)}</dd></div>
              </dl>
            </div>
          </section>

          <section className="overflow-hidden rounded-md border border-white/10 bg-[#121317]">
            <header className="flex items-center justify-between border-b border-white/10 px-3 py-2"><h2 className="text-[10px] font-bold uppercase text-zinc-400">Morphological metrics</h2><Activity className="h-3.5 w-3.5 text-zinc-600" /></header>
            <div className="p-3">
              <div className="mb-3 flex items-center justify-between"><strong className="font-mono text-xs text-zinc-300">INSTANCE DISTRIBUTIONS</strong><span className="text-[9px] uppercase text-zinc-600">First 28 instances</span></div>
              <div className="grid h-28 grid-cols-3 gap-2">
                <div className="relative border-b border-l border-white/10"><MetricBars values={areas} color="bg-blue-500" /><span className="absolute inset-x-0 bottom-1 text-center font-mono text-[8px] uppercase text-zinc-600">Area</span></div>
                <div className="relative border-b border-l border-white/10"><MetricBars values={perimeters} color="bg-fuchsia-500" /><span className="absolute inset-x-0 bottom-1 text-center font-mono text-[8px] uppercase text-zinc-600">Perimeter</span></div>
                <div className="relative border-b border-l border-white/10"><MetricBars values={eccentricities} color="bg-amber-400" /><span className="absolute inset-x-0 bottom-1 text-center font-mono text-[8px] uppercase text-zinc-600">Eccentricity</span></div>
              </div>
            </div>
          </section>

          <section className="overflow-hidden rounded-md border border-white/10 bg-[#121317]">
            <header className="flex items-center justify-between border-b border-white/10 px-3 py-2"><h2 className="text-[10px] font-bold uppercase text-zinc-400">Instance measurements</h2><TableProperties className="h-3.5 w-3.5 text-zinc-600" /></header>
            <div className="max-h-48 overflow-auto">
              <table className="w-full border-collapse font-mono text-[9px]"><thead className="sticky top-0 bg-[#17181d] text-zinc-600"><tr><th className="px-3 py-2 text-left">ID</th><th className="px-2 py-2 text-right">AREA</th><th className="px-2 py-2 text-right">PERIM.</th><th className="px-3 py-2 text-right">ECC.</th></tr></thead><tbody>{result.measurements.slice(0, 100).map((row) => <tr key={row.instance_id} className="border-t border-white/5 text-zinc-400"><td className="px-3 py-2">{row.instance_id}</td><td className="px-2 py-2 text-right">{row.area_px}</td><td className="px-2 py-2 text-right">{row.perimeter_px.toFixed(1)}</td><td className="px-3 py-2 text-right">{row.eccentricity.toFixed(3)}</td></tr>)}</tbody></table>
              {result.measurements.length === 0 && <p className="p-5 text-center text-[10px] text-zinc-600">No instances met the configured thresholds.</p>}
            </div>
          </section>

          {result.images.tta_disagreement && <section className="overflow-hidden rounded-md border border-white/10 bg-[#121317]">
            <header className="flex items-center justify-between border-b border-white/10 px-3 py-2"><h2 className="text-[10px] font-bold uppercase text-zinc-400">TTA disagreement map</h2><Gauge className="h-3.5 w-3.5 text-zinc-600" /></header>
            <button className="block w-full bg-black p-3 text-left" type="button" onClick={() => setActiveView('tta_disagreement')}><img className="h-28 w-full object-contain" src={dataUrl(result.images.tta_disagreement)} alt="TTA mask disagreement map" /><span className="mt-2 block text-[9px] font-mono uppercase text-zinc-600">Standard deviation across augmented views; not calibrated uncertainty</span></button>
          </section>}

          <section className="mb-4 overflow-hidden rounded-md border border-white/10 bg-[#121317]">
            <header className="border-b border-white/10 px-3 py-2"><h2 className="text-[10px] font-bold uppercase text-zinc-400">Report generation</h2></header>
            <div className="grid grid-cols-3 gap-2 p-3"><button className="flex items-center justify-center gap-2 rounded border border-white/10 bg-[#1c1d22] px-2 py-2 text-[9px] font-bold uppercase text-zinc-300 hover:bg-[#25262c]" type="button" onClick={() => downloadBase64(result.downloads.csv, 'text/csv', `${exportPrefix}-measurements.csv`)}><Download className="h-3.5 w-3.5" />CSV</button><button className="flex items-center justify-center gap-2 rounded border border-zinc-700 bg-zinc-800 px-2 py-2 text-[9px] font-bold uppercase text-white hover:bg-zinc-700" type="button" onClick={() => downloadBase64(result.downloads.pdf, 'application/pdf', `${exportPrefix}-report.pdf`)}><FileText className="h-3.5 w-3.5" />PDF</button><button className="flex items-center justify-center gap-2 rounded border border-white/10 bg-[#1c1d22] px-2 py-2 text-[9px] font-bold uppercase text-zinc-300 hover:bg-[#25262c]" type="button" onClick={() => downloadBase64(result.downloads.provenance_json, 'application/json', `${exportPrefix}-provenance.json`)}><Download className="h-3.5 w-3.5" />Proof</button></div>
          </section>
        </aside>
      </div>
    </motion.div>
  );
}
