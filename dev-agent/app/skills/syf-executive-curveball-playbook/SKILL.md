---
name: syf-executive-curveball-playbook
description: >-
  Use this skill when an executive or stakeholder introduces a mid-session scope change,
  architectural deprecation, volume surge, compliance mandate, or infrastructure constraint
  ("Wicked Curveball") that requires blast-radius recalculation across timeline, budget, and specs.
---

# Synchrony Financial Executive Curveball & Blast-Radius Playbook

This skill governs how Alex (`vpm-agent`) and Marcus (`arch-agent`) respond when an executive (such as Dan Weis) throws a mid-session architectural, financial, or regulatory curveball.

## 1. Mandatory 4-Step Curveball Response Protocol

Whenever a curveball is detected:
1. **Quantify Blast Radius (`evaluate_curveball_impact`)**:
   - Delegate to Marcus (`arch-agent`) to compute deterministic sprint delta, story point delta, budget impact, and affected architectural components using [curveball_decision_matrix.md](./references/curveball_decision_matrix.md).
   - If telemetry volume changes (e.g., `CB-2` 50M spans/mo surge), also consult Morgan (`finops-agent`) to recompute vendor TCO.
2. **Execute Cursor-Style Surgical Inline Patches (`patch_document_section`)**:
   - Patch `PRD-AI-EVAL-101.md` (specifically `## 4. Security, Ingress & Compliance Boundaries` and/or `## 5. Phased Rollout, Sprint Velocity & KPIs`) and `ADR-001-Eval-Gateway.md` in GCS.
   - Surface the unified line diff (`-` / `+`) directly in the conversation.
3. **Update Staged Backlog (`BACKLOG-AI-EVAL-101.json`)**:
   - Add or repoint the affected Jira stories while keeping `"status": "PENDING_APPROVAL"`.
4. **Enforce the Executive Human-in-the-Loop (HITL) Gate**:
   - Explicitly ask the executive: *"Do you approve the updated PRD/ADR diff, the revised sprint schedule, and the updated Jira backlog for commit?"*
   - Do NOT commit tickets to Jira or trigger Devin's scaffolding until explicit approval is received.
