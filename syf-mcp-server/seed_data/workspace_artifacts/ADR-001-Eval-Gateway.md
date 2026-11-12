# ADR-001: Architectural Decision Record — Synchrony Zero-Egress AI Evaluation & DLP Gateway

| Metadata Field | Value |
| :--- | :--- |
| **ADR ID** | `ADR-001-Eval-Gateway` |
| **Version** | `v1.0` |
| **Status** | `DRAFT` |
| **Architect** | Marcus (Enterprise Architect & CISO Governance Advisor) |
| **Product Owner** | Alex (Synchrony Virtual Product Manager) |
| **Linked PRD / Epic** | `PRD-AI-EVAL-101` / Jira Epic `SYF-5` (`AI-EVAL-101`) |

---

## 1. Context & Problem Statement
Synchrony Financial requires an enterprise-wide LLM evaluation and OpenTelemetry (OTel) observability platform for Credit Servicing, Fraud Operations, and **CareCredit** (Healthcare Financing). Because telemetry spans contain Tier-1 Cardholder Data (`PAN`, `SSN`) and CareCredit Protected Health Information (`MRN`, `ICD-10`), Synchrony's CISO mandates **100% Zero-Egress** inside Synchrony's private **AWS ROSA OpenShift VPC (`us-east-1`)** and **<25ms P95** inline ingestion latency across **5M to 50M monthly spans**.

---

## 2. Candidate Options Under Review (FinOps & CISO Audit Scope)
1. **Option A — Arize AX Enterprise (Multi-Tenant SaaS)**: `$85,000/yr` base + `$1,666.67/1M spans` (`$185,000/yr` at 5M spans/mo; `$1,085,000/yr` at 50M spans/mo). `38.0ms P95` cross-cloud ingestion latency.
2. **Option B — Braintrust Enterprise (Hybrid Cloud)**: `$60,000/yr` base + `$1,250.00/1M spans` (`$135,000/yr` at 5M spans/mo; `$804,000/yr` at 50M spans/mo). `24.0ms P95` hybrid proxy latency.
3. **Option C — Self-Hosted Langfuse Enterprise v3 on AWS ROSA OpenShift**: `$36,000/yr` Enterprise license + `$40,000/yr` ROSA OpenShift compute & ClickHouse v24.3 storage (`$76,000/yr` at 5M spans/mo; `$130,000/yr` at 50M spans/mo with `$0` per-span fees). `13.8ms P95` in-VPC ingestion latency.

---

## 3. Target Architecture & CISO Compliance Controls
- **Compute Runtime**: Red Hat UBI9 Python 3.12 non-root (`UID 1001`) FastAPI OpenTelemetry Collector & DLP Proxy deployed on AWS ROSA OpenShift 4.15 (`us-east-1`).
- **Inline Deterministic DLP Scrubber**: Compiled regex patterns via `json.dumps()`/`json.loads()` (`0` `eval()` calls) scrubbing `[REDACTED_PAN]`, `[REDACTED_SSN]`, `[REDACTED_MRN]`, and `[REDACTED_ICD10]` in `4.2ms` P95.
- **Identity & Auth**: Microsoft Entra ID OAuth 2.0 / OIDC JWT verification using an asynchronous local JWKS keyset cache (`300s` TTL, `1.8ms` overhead) + mTLS 1.3.
- **Storage Backend**: 3-node ZSTD-compressed ClickHouse v24.3 cluster (`10x` columnar compression) + PostgreSQL 16 inside Synchrony's private AWS ROSA VPC.
- **Ingress Topology (Baseline v1.0)**: North-South API traffic routes through **Kong Enterprise API Gateway v3.4** with TLS 1.3 termination and per-tenant rate limiting.
