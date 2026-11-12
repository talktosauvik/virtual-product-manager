# PRD-AI-EVAL-101: Synchrony Enterprise AI Evaluation & Observability Gateway

| Metadata Field | Value |
| :--- | :--- |
| **Document ID** | `PRD-AI-EVAL-101` |
| **Version** | `v1.0` |
| **Status** | `DRAFT` |
| **Product Owner** | Alex (Synchrony Virtual Product Manager) |
| **Target Architecture** | Self-Hosted Evaluation & DLP Gateway on AWS ROSA (OpenShift 4.15) |

---

## Section 1: Problem Statement & Executive Context

### 1.1 The Problem: Fragmented Evaluation & Zero-Egress Compliance Risk
Synchrony Financial operates mission-critical generative AI assistants across Credit Servicing, Collections, Fraud Operations, and **CareCredit** (Healthcare Financing). Today, engineering teams lack a unified, zero-egress observability platform to score faithfulness, toxicity, tool-selection accuracy, and prompt drift without risking external exposure of regulated Cardholder (`PAN`/`SSN`) and Healthcare (`MRN`/`ICD-10`) data.

### 1.2 Telemetry Scale Trajectory: 5M to 50M Monthly Spans (10x Surge)
Current production AI workloads generate **5,000,000 monthly OpenTelemetry (OTel) spans** at baseline, which is projected to scale **10x to 50,000,000 monthly spans** during the upcoming **9,000-seat GECX Contact Center** rollout. Usage-metered SaaS pricing models create severe cost escalation at this 50M-span volume.

### 1.3 What Synchrony Is Looking For
To solve the fragmentation problem (1.1) and absorb the 10x telemetry surge (1.2), Synchrony requires a centralized **Enterprise AI Evaluation & Observability Gateway** deployed 100% inside Synchrony's private **AWS ROSA (OpenShift 4.15) VPC** that delivers:
- **Zero-Egress Inline DLP Scrubbing** for PCI-DSS v4.0 and CareCredit HIPAA compliance.
- **Strict `<25ms P95` Ingestion Latency SLA** (engineered at **13.8ms P95**).
- **Predictable, Non-Metered TCO** from 5M to 50M+ monthly spans.

---

## Section 2: Candidate Vendor Evaluation Scope & FinOps Benchmarking Criteria
Morgan (FinOps & Vendor Economics Specialist) and Marcus (Enterprise Architect) are tasked with benchmarking three candidate LLM evaluation platforms across **5,000,000 monthly spans (Baseline)** and **50,000,000 monthly spans (10x GECX Contact Center Surge)**:

1. **Arize AX Enterprise (SaaS)** — Multi-tenant vendor cloud SaaS deployment model (`$85,000/yr` base platform license + per-span consumption metering).
2. **Braintrust Enterprise (Hybrid)** — Hybrid deployment model with an external SaaS control plane and an internal data plane proxy (`$60,000/yr` base platform license + per-span consumption metering).
3. **Langfuse Enterprise v3 (Self-Hosted on AWS ROSA OpenShift)** — 100% self-hosted containerized deployment inside Synchrony's private AWS ROSA OpenShift VPC (`$36,000/yr` Enterprise license + `$40,000/yr` ROSA OpenShift compute & ClickHouse storage, `$0` per-span fees).

---

## Section 3: Architecture & CISO Security Standards
All GenAI evaluation and telemetry traffic must route through an internal **FastAPI OpenTelemetry (OTel) Collector & DLP Proxy** running on **Red Hat OpenShift Service on AWS (ROSA 4.15, `us-east-1`)** using hardened **Red Hat UBI9 Python 3.12 non-root (`UID 1001`)** containers backed by a 3-node **ClickHouse v24.3** columnar analytics cluster and **PostgreSQL 16**.

| CISO Governance Domain | Mandatory Synchrony Standard | Target Architectural Implementation |
| :--- | :--- | :--- |
| **PCI-DSS v4.0 & CareCredit HIPAA Zero-Egress** | Zero external cloud egress for Tier-1 Cardholder Data (`PAN`, `SSN`) and CareCredit PHI (`MRN`, `ICD-10`). | Inline deterministic regex scrubbing (`[REDACTED_PAN]`, `[REDACTED_SSN]`, `[REDACTED_MRN]`, `[REDACTED_ICD10]`) via `json.dumps()`/`json.loads()` (`0` `eval()` calls) inside the FastAPI OTel Proxy before persistence to self-hosted ClickHouse inside AWS ROSA (`us-east-1`). |
| **Identity, Auth & Transport Encryption** | Microsoft Entra ID OAuth 2.0 / OIDC JWT authentication + Mutual TLS 1.3. | Asynchronous local JWKS public keyset cache (`300s` TTL, `1.8ms` verification overhead) validating Entra ID bearer tokens with strict mTLS 1.3 transport encryption. |
| **Inline DLP & Telemetry Ingestion Latency SLA (<25ms)** | End-to-end evaluation proxy and telemetry ingestion latency strictly `<25ms P95` inside Synchrony's AWS ROSA OpenShift VPC. | Engineered at **13.8ms P95** (`1.8ms` cached Entra ID JWKS auth + `4.2ms` inline regex DLP scrubbing + `7.8ms` async OTel protobuf ring-buffer batching) on Red Hat UBI9 non-root (`UID 1001`). |

---

## Section 4: API Gateway, DLP Scrubbing & Network Topology
- **Inline Deterministic DLP Redaction (`<15ms` budget)**: All incoming JSON/Protobuf telemetry spans are serialized via `json.dumps()`, scrubbed of 16-digit PANs, SSNs, CareCredit MRNs, and ICD-10 diagnostic codes (`[REDACTED_PAN]`, `[REDACTED_SSN]`, `[REDACTED_MRN]`, `[REDACTED_ICD10]`), and deserialized via `json.loads()` with **zero `eval()` usage**.
- **Identity & Transport Security**: Client SDKs authenticate using **Microsoft Entra ID OAuth 2.0 / OIDC** JWT bearer tokens (validated via a `300s` asynchronous JWKS cache) with end-to-end TLS 1.3 encryption.
- **API Gateway Ingress (Baseline v1.0)**: North-South API traffic routes through Synchrony's existing **Kong Enterprise API Gateway v3.4** with TLS 1.3 termination and per-tenant rate limiting.
