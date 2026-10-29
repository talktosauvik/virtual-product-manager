---
name: syf-sdlc-backlog-sync
description: >-
  Use this skill when translating approved PRD and ADR requirements into Jira Epics, Gherkin
  User Stories, Fibonacci story points, SYF squad assignments, Bitbucket feature branches,
  or synchronizing engineering ticket blockers back into the PRD.
---

# Synchrony Financial SDLC Backlog Decomposition & Continuous Blocker Sync Runbook

This skill governs how Alex (`vpm-agent`) and Devin (`dev-agent`) translate living PRD/ADR artifacts into Synchrony's Agile SDLC toolchain (Jira, Confluence, and Bitbucket) and handle continuous developer blocker loops.

## 1. Mandatory Human-in-the-Loop (HITL) Approval Gate

- **STRICT RULE**: You MUST NEVER call `create_jira_epic`, `create_jira_story`, `publish_confluence_prd`, or `create_bitbucket_branch_and_pr` until the human executive (e.g., Dan Weis) has explicitly approved the current PRD, ADR, and sprint/budget impact in the conversation.
- Before approval, save the proposed backlog draft to `BACKLOG-AI-EVAL-101.json` with `"status": "PENDING_APPROVAL"` and present the stories for sign-off.

## 2. Synchrony Jira Epic & Gherkin User Story Standards

Refer to [gherkin_story_schema.json](./resources/gherkin_story_schema.json) for the required JSON structure.

- **Epic Key**: `AI-EVAL-101` (`SYF-5`: `"Synchrony Enterprise GenAI Evaluation & Observability Gateway"`).
- **Agile Sprint Cadence**: 2-week sprints; industry-standard 4–5 developer squad velocity = **`32 Story Points / sprint`** (`$500/SP` = **`$16,000 / sprint`**).
- **Baseline 6-Sprint Plan**: `6 Sprints (12 Weeks) = 192 Total Story Points` (`48 SP` per baseline story across `SYF-6 / AI-STORY-101` .. `SYF-9 / AI-STORY-104`; delta curveball stories are sized at `32 SP` = `1 Sprint`).
- **Assigned Synchrony Engineering Squads**:
  - `SYF-Platform-Mesh-Squad` (OpenShift ROSA / Cloud Run deployment, Envoy Service Mesh mTLS, ClickHouse cluster)
  - `SYF-SecOps-DLP-Squad` (Inline PII/PCI/CareCredit HIPAA redaction middleware, Entra ID OAuth 2.0 JWKS auth)
  - `SYF-AI-FinOps-Squad` (OpenTelemetry `W3C TraceContext` collector proxy, Langfuse evaluation datasets, FinOps dashboards)
- **Acceptance Criteria Format**: Every story MUST include at least 2 structured **Gherkin (`Given / When / Then`)** acceptance criteria scenarios.

## 3. Continuous Lifecycle Blocker Sync (`sync_sdlc_ticket_blocker`)

When a developer updates a Jira ticket with an architectural or performance blocker (for example, `AI-STORY-102` hitting `42ms` P95 latency due to synchronous Entra ID token introspection):
1. Call `sync_sdlc_ticket_blocker(ticket_id=..., blocker_description=..., proposed_resolution=...)`.
2. Analyze the schedule and SLA impact (`0 sprint slip` if resolved via local 5-minute JWKS Redis/in-memory cache reducing auth latency to `1.8ms`).
3. Surgically patch `PRD-AI-EVAL-101.md` (`## 4. Security, Ingress & Compliance Boundaries`) and `ADR-001-Eval-Gateway.md` via `patch_document_section` so the product requirements stay continuously synchronized with engineering reality.
