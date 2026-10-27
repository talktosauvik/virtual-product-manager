---
name: syf-finops-tco-modeling
description: >-
  Use this skill when calculating Total Cost of Ownership (TCO), unit economics per million
  telemetry spans, or comparing AI evaluation vendors (Arize AX, Braintrust, Langfuse).
---

# Synchrony Financial FinOps TCO Modeling & Vendor Benchmark Runbook

This skill defines the standard methodology used by Morgan (`finops-agent`) and Alex (`vpm-agent`) to evaluate AI observability and evaluation platforms for Synchrony Financial.

## 1. Dual-Source Grounding Requirement

Every FinOps evaluation MUST combine:
1. **Live Web Intelligence (`google_search` via `deep_research_subagent`)**:
   - Verify current OpenTelemetry (`OTel` / `OpenInference`) protocol support, recent CVE security advisories, self-hosted Kubernetes/OpenShift Helm operator maturity, and licensing tier announcements for **Arize AX (Phoenix)**, **Braintrust**, and **Langfuse**.
2. **Internal Synchrony Financial Telemetry (`query_vendor_cost_benchmarks` via MCP)**:
   - Retrieve contracted enterprise license quotes, per-million span ingestion rates, and internal AWS ROSA / GCP Cloud Run infrastructure sizing costs from `eval_vendor_benchmarks.json`.

## 2. Synchrony Annual TCO Calculation Formula

Use the canonical formulas documented in [tco_formulas.md](./references/tco_formulas.md):

$$\text{Annual TCO (USD)} = L_{\text{base}} + \left(S_{\text{monthly\_M}} \times 12 \times C_{\text{span\_M}}\right) + I_{\text{compute}} + E_{\text{egress}}$$

Where:
- $L_{\text{base}}$: Annual enterprise base platform license fee.
- $S_{\text{monthly\_M}}$: Monthly telemetry span volume in millions (`5` for baseline pilot; `50` for full 9,000-seat GECX Contact Center rollout).
- $C_{\text{span\_M}}$: Vendor ingestion & retention fee per 1M spans (`$0` for self-hosted Langfuse).
- $I_{\text{compute}}$: Internal ROSA OpenShift / Cloud Run + ClickHouse storage & compute cost (`$40,000/yr` at 5M spans/mo; `$94,000/yr` at 50M spans/mo with 3-node ClickHouse sharding).
- $E_{\text{egress}}$: Cross-cloud VPC NAT/PrivateLink egress charges.

## 3. Required Output Format

Always present a side-by-side **FinOps Vendor Comparison Table** showing:
- Vendor & Deployment Topology
- Base Annual License ($L_{\text{base}}$)
- Annual Span Ingestion Cost at Target Volume ($5\text{M}$ and/or $50\text{M}$ spans/mo)
- Internal ROSA / Cloud Run Compute Cost ($I_{\text{compute}}$)
- **Total Annual TCO** & **Net Annual Savings vs. Arize SaaS**
- **FinOps Verdict** (`RECOMMENDED`, `BACKUP`, or `COST-PROHIBITIVE`)
