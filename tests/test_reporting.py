import numpy as np

from src.provenance import AnalysisProvenance
from src.reporting import analysis_pdf, build_artifacts, measurements_csv


def test_analysis_exports_are_nonempty() -> None:
    image = np.full((24, 24, 3), 220, dtype=np.uint8)
    instances = np.zeros((24, 24), dtype=np.int32)
    instances[4:10, 4:10] = 1
    instances[14:20, 14:20] = 2
    artifacts = build_artifacts(image, instances)
    assert len(artifacts.measurements) == 2
    assert artifacts.overlay.shape == image.shape
    assert measurements_csv(artifacts.measurements).startswith(b"instance_id")
    provenance = AnalysisProvenance.create(
        analysis_id="ANALYSIS-TEST",
        release_id="development",
        operating_mode="research",
        input_sha256="a" * 64,
        input_format="PNG",
        input_width=24,
        input_height=24,
        checkpoint_name="test.pt",
        checkpoint_sha256="b" * 64,
        runtime_device="CPU",
        settings={"use_tta": False, "mask_threshold": 0.5},
    )
    assert analysis_pdf(image, artifacts.overlay, instances > 0, 2, provenance).startswith(
        b"%PDF"
    )
