---
name: syf-prd-authoring
description: >-
  Use this skill when drafting a new Synchrony Financial Product Requirements Document (PRD)
  or performing Cursor-style surgical inline edits on specific sections of an existing PRD.
---

# Synchrony Financial PRD Authoring & Cursor-Style Editing Runbook

This skill governs how the Synchrony Virtual Product Manager (`vpm-agent` / Alex) drafts, structures, and surgically edits living Product Requirements Documents (`PRD-AI-EVAL-101.md`) in the shared Google Cloud Storage workspace (`gs://${PROJECT_ID}-syf-vpm-workspace/workspace_artifacts/`).

## 1. Mandatory Synchrony 5-Section PRD Schema

Every Synchrony Tier-1 AI Platform PRD MUST contain the following exact top-level Markdown section headers (`## N. ...`) so that surgical section-level patching (`patch_document_section`) can target any section deterministically:

1. `## 1. Executive Summary & Strategic Imperative`
   - Business context across Synchrony's 5 retail platforms (Digital, Health & Wellness / CareCredit, Home & Auto, Diversified & Value, Lifestyle) and 70M+ active cardholder accounts.
   - Alignment with Dan Weis (VP of AI Innovation) and Nimrod Barak (CAIO) AI Center of Excellence goals.
   - Core quantitative targets: `<25ms` P95 proxy latency overhead, `100%` OpenTelemetry (`W3C TraceContext`) trace capture, and `0` PII/PCI/HIPAA leakage incidents.
2. `## 2. FinOps TCO & Unit Economics`
   - Quantitative vendor benchmark matrix comparing **Arize AX Enterprise (SaaS)**, **Braintrust Enterprise (Hybrid)**, and **Langfuse Enterprise (Self-Hosted)** across baseline (`5M spans/month`) and GECX Contact Center scale (`50M spans/month`).
   - Annual savings calculation and unit cost per 1M telemetry spans.
3. `## 3. Target Multi-Cloud Architecture`
   - Selected evaluation control plane and data plane topology (e.g., Self-Hosted Langfuse Enterprise + ClickHouse cluster on AWS Red Hat OpenShift Service on AWS [ROSA] or Google Cloud Run Private Subnets).
   - Asynchronous FastAPI OpenTelemetry Collector Proxy architecture.
4. `## 4. Security, Ingress & Compliance Boundaries`
   - PCI-DSS v4.0 Tier-1 cardholder data (`PAN`, `CVV`, `SSN`) zero-egress policy.
   - CareCredit HIPAA Protected Health Information (`PHI`, `MRN`, `ICD-10`) inline scrubbing policy.
   - Identity & Ingress topology: Microsoft Entra ID OAuth 2.0 / OIDC JWT validation with local JWKS caching (`300s TTL`), strict mTLS (`TLS 1.3`), and API Gateway / Envoy Service Mesh routing (`mesh.syf.bank/injected: "true"`).
5. `## 5. Phased Rollout, Sprint Velocity & KPIs`
   - Sprint schedule (2-week Agile sprints, 20 story points/sprint/squad baseline), assigned Synchrony engineering squads, and release readiness gates.

For the starter Markdown template, inspect [prd_template.md](./resources/prd_template.md).

## 2. Cursor-Style Surgical Inline Editing Procedure

When a stakeholder (e.g., Dan Weis) highlights or references a specific section of the PRD—or throws an executive curveball that alters security, ingress, volume, or timeline:

1. **Do NOT overwrite the entire document** if `PRD-AI-EVAL-101.md` already exists in the workspace.
2. **Read the current living document** using `get_workspace_document(document_name="PRD-AI-EVAL-101.md")` if you need to inspect its current section text.
3. **Execute a surgical patch** using `patch_document_section`:
   - `document_name`: `"PRD-AI-EVAL-101.md"`
   - `section_header`: Exact header (e.g., `"## 4. Security, Ingress & Compliance Boundaries"` or `"## 5. Phased Rollout, Sprint Velocity & KPIs"`)
   - `new_section_markdown`: Complete updated Markdown for that section (including the `## N. ...` header line).
   - `edit_reason`: Concise audit summary (e.g., `"Replaced deprecated Kong Gateway v3.4 with Synchrony Envoy Service Mesh sidecar per CB-1"`).
4. **Render the Unified Diff Inline**:
   - Always include the `unified_diff` (`-` removed lines / `+` added lines) returned by `patch_document_section` inside a fenced ```` ```diff ```` block in your response so the executive can review exact line-level changes before approving.

## 3. Validation Checklist

- Verify `version` metadata increments (`1.0` -> `1.1` -> `1.2`) on every surgical patch.
- Verify all 5 canonical `## N.` headers remain intact in `PRD-AI-EVAL-101.md`.
- Confirm no Jira tickets are committed until the human stakeholder explicitly approves the updated PRD.
