export type AppState = 'idle' | 'processing' | 'results';
export type ResultView =
  | 'source'
  | 'overlay'
  | 'instances'
  | 'probability'
  | 'distance'
  | 'uncertainty';

export interface HealthStatus {
  status: 'ready' | 'setup_required' | 'invalid_checkpoint';
  ready: boolean;
  device: 'CPU' | 'CUDA' | 'MPS';
  checkpoint: string | null;
  checkpoint_sha256: string | null;
  detail: string | null;
}

export interface NucleusMeasurement {
  instance_id: number;
  area_px: number;
  perimeter_px: number;
  eccentricity: number;
  centroid_y: number;
  centroid_x: number;
}

export interface AnalysisResult {
  analysis_id: string;
  metrics: {
    nucleus_count: number;
    mean_area_px: number;
    mean_uncertainty: number;
  };
  images: {
    overlay: string;
    probability: string;
    instances: string;
    distance: string;
    uncertainty: string;
  };
  measurements: NucleusMeasurement[];
  downloads: {
    csv: string;
    pdf: string;
  };
}

export interface AnalysisOptions {
  useTta: boolean;
  maskThreshold: number;
  peakThreshold: number;
  minSize: number;
}

export interface AnalysisRequest {
  caseId: string;
  file: File;
  options: AnalysisOptions;
}
