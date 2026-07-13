import type {AnalysisOptions, AnalysisResult, HealthStatus} from './types';

async function responseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {detail?: string} | null;
    throw new Error(payload?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthStatus> {
  return responseJson<HealthStatus>(await fetch('/api/health'));
}

export async function analyzeImage(
  analysisId: string,
  file: File,
  options: AnalysisOptions,
  signal?: AbortSignal,
): Promise<AnalysisResult> {
  const data = new FormData();
  data.append('analysis_id', analysisId);
  data.append('file', file);
  data.append('use_tta', String(options.useTta));
  data.append('mask_threshold', String(options.maskThreshold));
  data.append('peak_threshold', String(options.peakThreshold));
  data.append('min_size', String(options.minSize));
  return responseJson<AnalysisResult>(
    await fetch('/api/analyze', {method: 'POST', body: data, signal}),
  );
}
