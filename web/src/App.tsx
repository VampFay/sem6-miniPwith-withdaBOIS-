import {AnimatePresence} from 'motion/react';
import {useCallback, useEffect, useRef, useState} from 'react';
import {analyzeImage, getHealth} from './api';
import {AppHeader} from './components/AppHeader';
import {DashboardView} from './components/DashboardView';
import {ProcessingView} from './components/ProcessingView';
import {UploadView} from './components/UploadView';
import type {AnalysisRequest, AnalysisResult, AppState, HealthStatus} from './types';

export default function App() {
  const [appState, setAppState] = useState<AppState>('idle');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [request, setRequest] = useState<AnalysisRequest | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const sourceUrlRef = useRef<string | null>(null);

  const refreshHealth = useCallback(async () => {
    try {
      setHealthError(null);
      setHealth(await getHealth());
    } catch (error) {
      setHealthError(error instanceof Error ? error.message : 'Inference API unavailable');
    }
  }, []);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  useEffect(() => () => {
    controllerRef.current?.abort();
    if (sourceUrlRef.current) URL.revokeObjectURL(sourceUrlRef.current);
  }, []);

  const clearAnalysis = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    if (sourceUrlRef.current) URL.revokeObjectURL(sourceUrlRef.current);
    sourceUrlRef.current = null;
    setSourceUrl(null);
    setRequest(null);
    setResult(null);
    setAnalysisError(null);
    setAppState('idle');
  }, []);

  const runAnalysis = useCallback(async (nextRequest: AnalysisRequest) => {
    controllerRef.current?.abort();
    if (sourceUrlRef.current) URL.revokeObjectURL(sourceUrlRef.current);

    const nextSourceUrl = URL.createObjectURL(nextRequest.file);
    const controller = new AbortController();
    sourceUrlRef.current = nextSourceUrl;
    controllerRef.current = controller;
    setSourceUrl(nextSourceUrl);
    setRequest(nextRequest);
    setResult(null);
    setAnalysisError(null);
    setAppState('processing');

    try {
      const nextResult = await analyzeImage(
        nextRequest.caseId,
        nextRequest.file,
        nextRequest.options,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setResult(nextResult);
      setAppState('results');
    } catch (error) {
      if (controller.signal.aborted) return;
      setAnalysisError(error instanceof Error ? error.message : 'Analysis failed');
      if (sourceUrlRef.current) URL.revokeObjectURL(sourceUrlRef.current);
      sourceUrlRef.current = null;
      setSourceUrl(null);
      setRequest(null);
      setAppState('idle');
    } finally {
      if (controllerRef.current === controller) controllerRef.current = null;
    }
  }, []);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden border border-white/5 bg-[#090a0c]">
      <AppHeader appState={appState} health={health} onNewCase={clearAnalysis} />
      <div className="relative flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          {appState === 'idle' && (
            <UploadView
              key="upload"
              health={health}
              healthError={healthError}
              analysisError={analysisError}
              onAnalyze={(nextRequest) => void runAnalysis(nextRequest)}
              onRefreshHealth={() => void refreshHealth()}
            />
          )}
          {appState === 'processing' && request && sourceUrl && (
            <ProcessingView
              key="processing"
              caseId={request.caseId}
              fileName={request.file.name}
              imageUrl={sourceUrl}
              health={health}
            />
          )}
          {appState === 'results' && request && sourceUrl && result && (
            <DashboardView
              key="results"
              result={result}
              sourceUrl={sourceUrl}
              caseId={request.caseId}
              fileName={request.file.name}
              options={request.options}
              health={health}
              onReset={clearAnalysis}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
