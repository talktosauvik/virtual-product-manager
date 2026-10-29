---
document_id: PRD-AI-EVAL-101
title: Synchrony Enterprise GenAI Evaluation & Observability Gateway
owner: Alex (SYF Virtual Product Manager)
sponsor: Dan Weis (VP of AI Innovation) & Nimrod Barak (CAIO)
status: DRAFT
version: "1.0"
---

# PRD-AI-EVAL-101: Enterprise GenAI Evaluation & Observability Gateway

## 1. Executive Summary & Strategic Imperative
- **Business Objective**: Establish a unified, zero-egress GenAI evaluation and OpenTelemetry (`W3C TraceContext`) observability platform supporting Synchrony's 5 retail credit platforms, CareCredit health & wellness portfolio, and 9,000+ GECX contact center agents.
- **Target SLAs**: `<25ms` P95 inline proxy latency overhead; `100%` trace span capture; `0` unredacted PII/PCI/HIPAA telemetry egress events.

## 2. FinOps TCO & Unit Economics
| Vendor | Deployment Model | 5M Spans/Mo Annual TCO | 50M Spans/Mo Annual TCO | PCI/HIPAA Zero-Egress | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Arize AX Enterprise** | Multi-Tenant SaaS | $185,000/yr | $1,085,000/yr | Non-Compliant (Rejected) | Rejected |
| **Braintrust Enterprise** | Hybrid Cloud | $135,000/yr | $804,000/yr | Partial (Control Plane Egress) | Backup Only |
| **Langfuse Enterprise** | Self-Hosted (ROSA / Cloud Run) | **$76,000/yr** | **$130,000/yr** | **100% Compliant** | **Selected ($109k–$955k/yr Savings)** |

## 3. Target Multi-Cloud Architecture
- **Control & Storage Plane**: Self-Hosted Langfuse Enterprise v3 backed by ClickHouse and PostgreSQL inside Synchrony's private VPC (AWS Red Hat OpenShift Service on AWS [ROSA] with portable deployment to Google Cloud Run Private Subnets).
- **Ingestion Data Plane**: Asynchronous Python 3.12 FastAPI OpenTelemetry Collector Proxy (`syf-eval-gateway`) running on hardened Red Hat UBI9 containers (`UID 1001`).

## 4. Security, Ingress & Compliance Boundaries
- **PCI-DSS v4.0 & CareCredit HIPAA Compliance**: Zero external SaaS egress for Tier-1 cardholder data (`PAN`, `SSN`) and CareCredit Protected Health Information (`MRN`, `ICD-10`). Mandatory inline regex/DLP scrubbing prior to span persistence.
- **Identity & Access Management**: Microsoft Entra ID OAuth 2.0 / OIDC JWT bearer authentication with strict mutual TLS (`mTLS 1.3`).
- **Network Ingress Topology (Baseline v1.0)**: Kong Enterprise API Gateway v3.4 (`kong-ingress.syf.bank`) terminating north-south and east-west OpenTelemetry trace ingestion into the FastAPI evaluation proxy.

## 5. Phased Rollout, Sprint Velocity & KPIs
- **Baseline Delivery Plan**: **6 Sprints (12 Weeks / 192 Total Story Points)** across `SYF-Platform-Mesh-Squad`, `SYF-SecOps-DLP-Squad`, and `SYF-AI-FinOps-Squad` (industry-standard Agile velocity baseline: **32 Story Points per 2-week sprint** for a 4–5 developer squad at `$500/SP` = `$16,000/sprint`).
- **Release Gate**: Requires explicit executive Human-in-the-Loop (HITL) sign-off prior to Jira Epic/Story creation and Bitbucket repository scaffolding.
