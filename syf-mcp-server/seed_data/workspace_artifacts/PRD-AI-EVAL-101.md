---
document_id: PRD-AI-EVAL-101
title: Synchrony Enterprise GenAI Evaluation & Observability Gateway
owner: Alex (Principal Virtual Product Manager, Synchrony Financial)
status: DRAFT
version: "1.0"
last_modified_by: Alex (vpm-agent)
---

# PRD-AI-EVAL-101: Enterprise GenAI Evaluation & Observability Gateway

## 1. Executive Summary & Strategic Imperative
Synchrony Financial (SYF) is standardizing GenAI evaluation, prompt telemetry, and OpenTelemetry (`W3C TraceContext`) observability across its 5 core retail credit platforms, CareCredit health & wellness financing portfolio, and 9,000+ GECX contact center agents.
- **Primary Business Goal**: Establish a single, zero-egress GenAI evaluation and telemetry gateway (`syf-eval-gateway`) that empowers product and engineering squads to benchmark LLM quality, detect drift, and attribute token/span FinOps costs without exposing regulated customer data.
- **Mandatory SLAs**:
  - **Inline Proxy Latency Overhead**: `<25ms` P95 (baseline target `14.0ms` P95 across AWS ROSA `us-east-1` and GCP Vertex AI `us-central1`).
  - **Trace Context Propagation**: `100%` W3C `traceparent` header compliance across multi-agent and RAG pipelines.
  - **Zero Data Leakage**: `0` unredacted PCI-DSS v4.0 (`PAN`, `SSN`) or CareCredit HIPAA (`MRN`, `ICD-10`) spans leaving Synchrony VPC boundaries.

## 2. FinOps TCO & Unit Economics (5M vs. 50M Spans/Month)
| Vendor | Deployment Model | 5M Spans/Mo Annual TCO | 50M Spans/Mo Annual TCO | PCI/HIPAA Zero-Egress | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Arize AX Enterprise** | Multi-Tenant SaaS | $185,000/yr | $1,085,000/yr | Non-Compliant (SaaS Egress) | **REJECTED** |
| **Braintrust Enterprise** | Hybrid Cloud | $135,000/yr | $804,000/yr | Conditional (Control Plane Egress) | **REJECTED** |
| **Langfuse Enterprise v3** | Self-Hosted (SYF VPC) | **$76,000/yr** | **$130,000/yr** | **100% Zero-Egress Compliant** | **APPROVED ($109k–$955k/yr Savings)** |

## 3. Target Multi-Cloud Architecture & Latency Guardrails
- **Evaluation Control & Storage Plane**: Self-Hosted **Langfuse Enterprise v3** backed by columnar ClickHouse storage and PostgreSQL deployed inside Synchrony's private VPC on **AWS Red Hat OpenShift Service on AWS (ROSA)** (with portable container compatibility for **Google Cloud Run Private Subnets**).
- **Telemetry Ingestion Data Plane**: High-throughput asynchronous Python 3.12 **FastAPI OpenTelemetry Collector Proxy (`syf-eval-gateway`)** built on hardened Red Hat UBI9 (`registry.access.redhat.com/ubi9/python-312:latest`, non-root `UID 1001`).

## 4. Security, Ingress & Compliance Boundaries
- **PCI-DSS v4.0 & CareCredit HIPAA Scrubbing**: Inline deterministic JSON serialization (`json.dumps` / `json.loads`—zero `eval()`) with compiled regex redaction for 16-digit PAN (`[REDACTED_PAN]`), 9-digit SSN (`[REDACTED_SSN]`), and CareCredit Medical Record Numbers (`[REDACTED_MRN]`, `[REDACTED_PHI]`) enforced alongside Google Cloud Model Armor (`syf-pci-hipaa-strict-v2`).
- **Identity & Access Management**: Microsoft Entra ID OAuth 2.0 / OIDC JWT bearer token validation and strict mutual TLS (`mTLS 1.3`) across all evaluation gateway endpoints.
- **API Ingress Topology**: North-South and East-West API gateway ingress routed via Synchrony's existing **Kong Enterprise API Gateway v3.4** with TLS 1.3 termination and per-tenant rate limiting.

## 5. Phased Rollout, Sprint Velocity & KPIs
- **Baseline Delivery Schedule**: **6 Sprints (12 Weeks, 192 Total Story Points)** at an industry-standard squad velocity of **32 Story Points per 2-week sprint** (4–5 developers per squad; `$500/SP` blended rate = `$16,000/sprint`) across `SYF-Platform-Mesh-Squad`, `SYF-AI-FinOps-Squad`, and `SYF-SecOps-DLP-Squad`.
- **Baseline Annual Infrastructure & License Run-Rate**: **`$76,000/yr`** at 5M monthly spans (`$36,000` Langfuse Enterprise license + `$40,000` ROSA ClickHouse compute).
- **Governance Gate**: All Jira backlog mutations, Confluence status promotions, and Bitbucket code scaffolding are gated behind explicit executive Human-in-the-Loop (HITL) approval.
