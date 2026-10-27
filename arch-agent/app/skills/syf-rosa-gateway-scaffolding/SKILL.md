---
name: syf-rosa-gateway-scaffolding
description: >-
  Use this skill when generating production-ready container images, FastAPI OpenTelemetry
  collector proxies, inline PII/PCI/HIPAA redaction middleware, and OpenShift (ROSA) or
  Cloud Run deployment manifests.
---

# Synchrony Financial Golden Microservice & OpenShift (ROSA) Scaffolding Runbook

This skill governs how Devin (`dev-agent`) generates production-ready microservice code for Synchrony's Evaluation & Observability Gateway (`syf-eval-gateway`) and persists the artifacts to `gs://${PROJECT_ID}-syf-vpm-workspace/scaffolded_code/`.

## 1. Mandatory Golden Engineering Standards

Refer to [golden_templates.md](./resources/golden_templates.md) for verified production code templates.

1. **Red Hat UBI9 Hardened Container (`Dockerfile`)**:
   - Base image MUST be `registry.access.redhat.com/ubi9/python-312:latest`.
   - Must drop root privileges and execute as non-root OpenShift-compatible UID `1001`.
   - Expose port `8080` and launch `uvicorn proxy_gateway:app --host 0.0.0.0 --port 8080`.

2. **FastAPI OpenTelemetry Proxy & Safe PII/PCI/HIPAA Scrubber (`proxy_gateway.py`)**:
   - **CRITICAL SECURITY MANDATE (Zero `eval()`)**: Never use Python's `eval()` to deserialize sanitized payloads. Always serialize the dict via `json.dumps(payload)`, run compiled regex replacements, and parse back via `json.loads(sanitized_json)`.
   - **Regex Patterns Required**:
     - `PAN_REGEX`: `\b(?:\d[ -]*?){13,16}\b` -> `"[REDACTED_PAN]"`
     - `SSN_REGEX`: `\b\d{3}-\d{2}-\d{4}\b` -> `"[REDACTED_SSN]"`
     - `MRN_REGEX`: `\bMRN-\d{6,10}\b` -> `"[REDACTED_MRN]"`
   - **W3C TraceContext Propagation**: Read `traceparent` header (or synthesize a compliant `00-<32hex>-<16hex>-01` header) and forward asynchronously via `httpx.AsyncClient` to the internal Langfuse ingestion endpoint within `<25ms` P95 latency.
   - **Entra ID Local JWKS Cache**: Validate Bearer JWT tokens against a cached JWKS keyset (`TTL=300s`) so auth overhead remains `<2ms`.

3. **OpenShift (ROSA) & Envoy Service Mesh Manifest (`k8s_deployment.yaml`)**:
   - Pod annotations MUST include:
     - `mesh.syf.bank/injected: "true"` (Synchrony Envoy Service Mesh mTLS 1.3 sidecar)
     - `security.syf.bank/pci-tier: "tier-1-redacted"`
     - `prometheus.io/scrape: "true"`
   - Include readiness (`/healthz`) and liveness (`/livez`) probes.
