---
document_id: PRD-AI-EVAL-101
title: Synchrony Enterprise GenAI Evaluation & Observability Gateway
owner: Alex (SYF Virtual Product Manager)
sponsor: Dan Weis (VP of AI Innovation) & Nimrod Barak (CAIO)
status: DRAFT
version: "1.0"
last_modified_by: Alex (vpm-agent)
---

# PRD-AI-EVAL-101: Enterprise GenAI Evaluation & Observability Gateway

## 1. Executive Summary & Strategic Imperative
Synchrony Financial (SYF) is standardizing GenAI evaluation, prompt telemetry, and OpenTelemetry (`W3C TraceContext`) observability across its 5 core retail credit platforms, CareCredit health & wellness financing portfolio, and 9,000+ GECX contact center agents.
- **Primary Business Goal**: Establish a single, zero-egress GenAI evaluation and telemetry gateway that empowers product and engineering squads to benchmark LLM quality, detect drift, and attribute token/span FinOps costs without exposing regulated customer data.
- **Mandatory SLAs**:
  - **Inline Proxy Latency Overhead**: `<25ms` P95 (target `14.2ms` P95).
  - **Trace Context Propagation**: `100%` W3C `traceparent` header compliance across multi-agent and RAG pipelines.
  - **Zero Data Leakage**: `0` unredacted PCI-DSS v4.0 (`PAN`, `SSN`) or CareCredit HIPAA (`MRN`, `ICD-10`) spans leaving Synchrony VPC boundaries.

## 2. FinOps TCO & Unit Economics
| Vendor | Deployment Model | 5M Spans/Mo Annual TCO | 50M Spans/Mo Annual TCO | PCI/HIPAA Zero-Egress | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Arize AX Enterprise** | Multi-Tenant SaaS | $185,000/yr | $1,085,000/yr | Non-Compliant (SaaS Egress) | **REJECTED** |
| **Braintrust Enterprise** | Hybrid Cloud | $147,000/yr | $804,000/yr | Conditional (Control Plane Egress) | **BACKUP ONLY** |
| **Langfuse Enterprise** | Self-Hosted (SYF VPC) | **$76,000/yr** | **$130,000/yr** | **100% Zero-Egress Compliant** | **SELECTED ($109k–$955k/yr Savings)** |

## 3. Target Multi-Cloud Architecture
- **Evaluation Control & Storage Plane**: Self-Hosted **Langfuse Enterprise v3** backed by ClickHouse and PostgreSQL deployed inside Synchrony's private VPC on **AWS Red Hat OpenShift Service on AWS (ROSA)** (with portable container compatibility for **Google Cloud Run Private Subnets**).
- **Telemetry Ingestion Data Plane**: High-throughput asynchronous Python 3.12 **FastAPI OpenTelemetry Collector Proxy (`syf-eval-gateway`)** built on hardened Red Hat UBI9 (`registry.access.redhat.com/ubi9/python-312:latest`, non-root UID `1001`).

## 4. Security, Ingress & Compliance Boundaries
- **PCI-DSS v4.0 & CareCredit HIPAA Scrubbing**: Inline deterministic JSON serialization (`json.dumps` / `json.loads`—zero `eval()`) with compiled regex redaction for 16-digit PAN (`[REDACTED_PAN]`), 9-digit SSN (`[REDACTED_SSN]`), and CareCredit Medical Record Numbers (`[REDACTED_MRN]`).
- **Identity & Access Management**: Microsoft Entra ID OAuth 2.0 / OIDC JWT bearer authentication with local in-memory JWKS keyset caching (`300s TTL`, `<2ms` verification overhead) and mutual TLS (`mTLS 1.3`).
- **API Ingress Topology**: Baseline ingress routed via legacy Kong Enterprise Gateway v3.4 *(Pending Architecture Review Board migration to Synchrony Envoy Service Mesh `mesh.syf.bank/injected: "true"` per Q1 Kong deprecation notice)*.

## 5. Phased Rollout, Sprint Velocity & KPIs
- **Baseline Delivery Schedule**: **3 Sprints (6 Weeks)** at 20 story points/sprint/squad across `SYF-Platform-Mesh-Squad`, `SYF-AI-FinOps-Squad`, and `SYF-SecOps-DLP-Squad`.
- **Governance Gate**: Requires explicit executive Human-in-the-Loop (HITL) approval before committing Epics/Stories to Jira or scaffolding code into Bitbucket.
