---
name: syf-zero-trust-compliance
description: >-
  Use this skill when evaluating system architectures against Synchrony Financial's CISO and CTO
  standards, including PCI-DSS v4.0, CareCredit HIPAA PHI rules, Microsoft Entra ID mTLS/JWKS,
  and API gateway / service mesh topology, or when authoring an Architecture Decision Record (ADR).
---

# Synchrony Financial Zero-Trust Security, PCI/HIPAA Compliance & ADR Runbook

This skill defines the enterprise architecture and InfoSec validation rules enforced by Marcus (`arch-agent`) and Alex (`vpm-agent`) across all Synchrony Financial GenAI workloads.

## 1. Non-Negotiable CISO & CTO Compliance Mandates

Refer to [pci_hipaa_entraid_rules.md](./references/pci_hipaa_entraid_rules.md) for full control mappings.

1. **Zero-Egress Data Residency (PCI-DSS v4.0 + CareCredit HIPAA)**:
   - Any platform ingesting LLM prompts, completions, or OpenTelemetry spans from Tier-1 retail credit applications or CareCredit healthcare financing flows MUST run **100% inside Synchrony-controlled VPCs** (AWS Red Hat OpenShift Service on AWS [ROSA] or Google Cloud Run Private Subnets).
   - **Multi-Tenant SaaS Egress (`Arize AX SaaS`)**: Immediately flag as `NON-COMPLIANT / REJECTED`.
   - **Hybrid Control Plane Egress (`Braintrust Hybrid`)**: Flag as `CONDITIONAL / HIGH RISK` due to metadata/prompt-template synchronization with external vendor cloud.
   - **Self-Hosted Container (`Langfuse Enterprise Self-Hosted`)**: Flag as `APPROVED / 100% COMPLIANT`.

2. **Identity, Authentication & Encryption in Transit**:
   - **Authentication**: Microsoft Entra ID OAuth 2.0 / OIDC JWT bearer tokens required on every telemetry ingestion endpoint.
   - **Latency Guardrail (`<25ms` P95)**: Never perform synchronous per-request token introspection against Entra ID over the WAN. Enforce **local in-memory JWKS public key caching (`300s TTL`)** inside the FastAPI proxy (`<2ms` verification overhead).
   - **Transport Security**: Strict mutual TLS (`mTLS 1.3`) enforced via Envoy sidecar certificates.

3. **Gateway & Service Mesh Topology (CRITICAL Q1 Deprecation)**:
   - **Deprecated Component**: **Kong Enterprise Gateway v3.4 is officially deprecated effective Q1**. No new Tier-1 GenAI services may route through Kong.
   - **Approved Replacement**: **Synchrony Internal Service Mesh (Envoy sidecar injection: `mesh.syf.bank/injected: "true"`)** for east-west telemetry traffic, paired with **Apigee Hybrid** for north-south ingress.

## 2. Architecture Decision Record (`ADR-001-Eval-Gateway.md`) Schema

Every Synchrony ADR stored in `gs://${PROJECT_ID}-syf-vpm-workspace/workspace_artifacts/ADR-001-Eval-Gateway.md` MUST maintain these 5 sections:
- `## 1. Context & Problem Statement`
- `## 2. FinOps vs. Security Trade-Off Analysis (Morgan vs. Marcus)`
- `## 3. Decision Outcome & Selected Architecture`
- `## 4. Network Ingress, Identity & Inline DLP Controls`
- `## 5. Consequences, Blast Radius & Operational SLAs`
