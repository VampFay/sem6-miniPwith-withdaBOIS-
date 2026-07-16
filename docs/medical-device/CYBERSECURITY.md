# Cybersecurity and Privacy Plan

## Trust boundaries

The browser, uploaded file, analysis ID, and client parameters are untrusted. Controlled deployment
places the service behind an organization-managed TLS identity gateway. The gateway authenticates
the user, enforces role/site policy, strips spoofable inbound identity headers, and injects the
service credential plus canonical `X-Actor-ID`. The credential must never be shipped to browser
code. Health endpoints expose no filesystem path or secret.

The model is a read-only, digest-approved artifact. The container runs non-root with a read-only
filesystem and bounded temporary storage. Audit storage is separate, access controlled, backed up,
retention governed, and exported to an independently protected log service; the local hash chain
detects alteration but is not a substitute for an external immutable anchor.

The production candidate is pinned to an immutable Wolfi base and exact Python 3.12 package version,
runs non-root as UID/GID 65532, and removes the runtime shell and package manager. Dependencies are
installed from the hash lock in a separate pinned build stage and copied into the runtime. This
reduces attack surface but does not waive clean image scanning, SBOM review, native-library testing,
or vulnerability disposition for every frozen release.

## Required release controls

- threat model covering upload/parser, dependency/supply chain, API abuse, identity spoofing,
  model replacement, audit destruction, report exfiltration, denial of service, and operator error;
- pinned reproducible build, SBOM for application/container/model/data, signature/attestation, secret
  scanning, SAST, dependency/container/IaC scanning, image fuzzing, DAST and penetration testing;
- rate/concurrency/body/time limits at the gateway; TLS 1.2+ policy; network segmentation; no
  unrestricted egress; centralized redacted logs and alerts;
- managed secret rotation, least privilege, vulnerability intake/triage, coordinated disclosure,
  patch SLA, incident response, recovery exercise, and regulator/customer notification procedure;
- DPIA/privacy review, data-flow inventory, lawful basis/consent, minimization, retention/deletion,
  backup handling, subject rights, cross-border rules, and business-associate/data-processing terms.

The current bearer service credential is an upstream service-authentication control, not a complete
RBAC or human identity system. Direct controlled exposure of the FastAPI service is prohibited.
As defense in depth, the application independently caps the complete `/api/analyze` body before
multipart parsing, counts streamed bodies without `Content-Length`, then separately enforces file
bytes and decoded pixels. Configure both the file limit and bounded multipart overhead from approved
site requirements; this does not replace gateway concurrency, rate, or timeout enforcement.
For every successful controlled analysis, the gateway or protected log collector must retain the
returned audit `sequence`, record SHA-256, and previous-record SHA-256. Sequence gaps or a mismatch
with the exported local `.chain-head` are incident conditions.

## Runtime SBOM evidence

Generate the runtime dependency SBOM from the committed hash lock, never from an uncontrolled local
environment:

```bash
./setup.sh sbom outputs_v2/release/sbom.cdx.json
```

The command queries the vulnerability service, writes a CycloneDX JSON document, and writes an
adjacent `.receipt.json` binding the requirements-lock SHA-256, SBOM SHA-256, generator, component
and vulnerability counts, audit exit code, and release disposition. Any dependency-collection
failure or reported vulnerability makes the command fail. Preserve both files with the signed build
record. This covers the Python runtime dependency SBOM only; the release still requires separately
signed container, operating-system, model, data, frontend, and infrastructure inventories/scans.

CI now runs immutable-SHA-pinned CodeQL `security-extended` analysis for Python and
JavaScript/TypeScript, a high/critical Trivy OS/library image gate, a repository
misconfiguration/secret gate, and container CycloneDX generation with retained artifacts. The Trivy
Action is pinned to the verified post-incident v0.36.0 commit rather than a mutable tag. These jobs
must execute successfully on the frozen commit and their raw SARIF/log/SBOM evidence must be retained
under QMS control; workflow configuration alone is not release evidence. Independent penetration,
DAST, image fuzzing, license review, infrastructure scanning, and supplier assessment remain
mandatory.
