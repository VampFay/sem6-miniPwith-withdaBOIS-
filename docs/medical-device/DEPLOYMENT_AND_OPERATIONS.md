# Controlled Deployment and Operations

## Supported topology

Client → managed TLS/OIDC gateway/WAF → one Attn-Dist-Net worker per accelerator. The gateway owns
human authentication, RBAC, site policy, rate/timeout/body limits, and trusted actor-header
injection. The API model mount is read-only; the application filesystem is read-only; audit storage
is a restricted durable mount; logs/metrics go to managed systems with PHI-safe schemas. Direct
internet or laboratory-client access to port 8000 is prohibited.

The supplied hash-locked container is a CPU runtime. GPU acceleration requires a separately locked,
scanned, performance-qualified, and clinically regression-tested image for the exact driver and
accelerator stack; changing the PyTorch hardware build is a controlled release change.
The supplied runtime is shell-less and package-manager-free, runs as numeric UID/GID 65532, and
uses Python 3.11; site volume ownership and security policy must preserve that identity. Do not add
diagnostic tools to the production image—use an independently controlled debug image and incident
procedure when investigation requires them.

## Required environment

```text
ATTNDIST_OPERATING_MODE=controlled
ATTNDIST_RELEASE_ID=<approved release identifier>
ATTNDIST_CHECKPOINT=/models/<approved artifact>.pt
ATTNDIST_APPROVED_CHECKPOINT_SHA256=<64 lowercase hex characters>
ATTNDIST_AUDIT_DIR=/audit
ATTNDIST_API_TOKEN=<secret manager injection, at least 32 characters>
ATTNDIST_SBOM_RECEIPT=<repository-contained approved .receipt.json path>
ATTNDIST_ALLOWED_ORIGINS=https://<approved workstation origin>
ATTNDIST_ENABLE_DOCS=0
ATTNDIST_MAX_UPLOAD_BYTES=<approved file-byte limit>
ATTNDIST_MAX_MULTIPART_OVERHEAD_BYTES=<approved form-overhead allowance>
ATTNDIST_MAX_IMAGE_PIXELS=<approved decoded-pixel limit>
```

The gateway injects `Authorization: Bearer <service token>` and canonical `X-Actor-ID`; neither is
entered by an end user or embedded in the UI. Run `./setup.sh release-gate` in the final runtime
configuration. Readiness must be green before routing traffic.
The complete request limit is the upload limit plus multipart-overhead allowance and is enforced
before multipart parsing even for streamed bodies; the gateway must independently enforce an equal
or stricter body limit together with qualified concurrency and time limits.

Before installation qualification, generate `./setup.sh sbom <controlled-output-path>` and retain
the CycloneDX document plus receipt with the source, image, checkpoint, and release hashes. Export
the local audit chain head after every accepted event to independently protected storage; the local
head detects suffix deletion on the application volume but cannot resist an attacker able to rewrite
both records and head.

Audit schema version 1 uses contiguous 20-digit sequence filenames, a process lock, and
`.chain-head`. Timestamp-named development records from earlier builds are rejected rather than
silently migrated. Upgrade procedures must archive and verify the old chain, start a new controlled
chain with an approved linkage record, and preserve both under retention policy. Qualify advisory
file locking, atomic replacement, directory `fsync`, permissions, backup, and recovery on the exact
audit filesystem; do not assume every network filesystem provides the required semantics.

## Site qualification and operations

Installation qualification records hardware/OS/container/model/release hashes, gateway policies,
time synchronization, certificates, display/browser, audit permissions, backup, monitoring, and
network segmentation. Operational qualification executes approved positive/negative samples,
format/size/auth/model/audit failures, recovery, concurrency/latency, backup restore and rollback.
Performance qualification uses representative local workflow samples under an approved protocol.
Run the bounded load harness with site-approved limits, for example:

```bash
./setup.sh load-test qualified-synthetic.png --url https://validated-host \
  --requests 100 --concurrency 4 --max-p95-ms 5000 --max-error-rate 0
```

Acceptance limits must come from workflow requirements and qualified hardware; the example is not
a product specification. Use non-patient qualification images unless governance explicitly allows
otherwise.

Monitor readiness, latency, failures by category, resource saturation, authentication failures,
audit export/chain status, input distributions, rejection/override patterns, and approved clinical
performance signals without placing pixels or identifiers in general logs. Define on-call ownership,
severity, downtime workflow, complaint routing, backup retention, RTO/RPO, and disaster exercises.

Rollback restores a previously approved signed container/model pair and never mixes model,
postprocessing, labeling, or UI versions. Emergency changes follow documented deviation and
retrospective CAPA; they do not bypass clinical/regulatory assessment.
