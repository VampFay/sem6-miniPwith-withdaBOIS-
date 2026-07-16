export type AppState = 'idle' | 'processing' | 'results';
export type ResultView =
  | 'source'
  | 'overlay'
  | 'instances'
  | 'foreground_score'
  | 'distance'
  | 'tta_disagreement';

export interface HealthStatus {
  status: 'ready' | 'setup_required' | 'invalid_checkpoint' | 'configuration_error';
  ready: boolean;
  operating_mode: 'research' | 'controlled' | 'invalid';
  release_id: string | null;
  device: 'CPU' | 'CUDA' | 'MPS';
  checkpoint: string | null;
  checkpoint_sha256: string | null;
  postprocessing: {
    mask_threshold: number;
    peak_threshold: number;
    min_size: number;
    gaussian_sigma: number;
    peak_window_size: number;
  } | null;
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
  provenance: {
    analysis_uuid: string;
    analysis_id: string;
    created_at_utc: string;
    software_version: string;
    release_id: string;
    operating_mode: 'research' | 'controlled';
    input_sha256: string;
    input_format: string;
    input_width: number;
    input_height: number;
    checkpoint_name: string;
    checkpoint_sha256: string;
    runtime_device: string;
    settings: Record<string, boolean | number>;
  };
  audit_receipt: {
    sequence: number;
    record_sha256: string;
    previous_record_sha256: string | null;
  } | null;
  settings: {
    use_tta: boolean;
    mask_threshold: number;
    peak_threshold: number;
    min_size: number;
    gaussian_sigma: number;
    peak_window_size: number;
  };
  metrics: {
    nucleus_count: number;
    mean_area_px: number;
    mean_tta_disagreement: number | null;
  };
  images: {
    overlay: string;
    foreground_score: string;
    instances: string;
    distance: string;
    tta_disagreement: string | null;
  };
  measurements: NucleusMeasurement[];
  downloads: {
    csv: string;
    pdf: string;
    provenance_json: string;
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
