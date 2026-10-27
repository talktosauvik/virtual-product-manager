# Synchrony Financial (SYF) — Virtual Product Manager (VPM) Multi-Agent Platform

An enterprise-grade multi-agent platform built on **Google Cloud Agent Development Kit (ADK)**, **Vertex AI Agent Runtime**, **Google Cloud Run (A2A)**, and **FastMCP** that brings **"Cursor-style" multi-file product management**, **Antigravity Skills**, and **automated SDLC execution** (Confluence, Jira, Bitbucket) to Synchrony Financial.

---

## Architecture & Agent Fleet

| Component | Persona & Role | Model & Thinking Config | Runtime Target | Identity |
| :--- | :--- | :--- | :--- | :--- |
| **[`vpm-agent`](./vpm-agent)** | **Alex** — Root Virtual PM Orchestrator ("Mimic Cursor" Multi-File Diffs, Antigravity Skills, Vertex Memory Bank, HITL Gate) | `gemini-3.8-flash` (`MEDIUM`) | **Vertex AI Agent Runtime** (`ReasoningEngine`) | SPIFFE Principal |
| **[`finops-agent`](./finops-agent)** | **Morgan** — Deep Research & FinOps Analyst (Vertex AI Search + Live Google Search + 3-Year TCO Calculator) | `gemini-3.5-flash-lite` (`LOW`) | **Vertex AI Agent Runtime** (`ReasoningEngine`) | SPIFFE Principal |
| **[`arch-agent`](./arch-agent)** | **Marcus** — Enterprise Architecture & OCC/PCI-DSS 4.0 Compliance Specialist | `gemini-3.5-flash-lite` (`LOW`) | **Google Cloud Run** (A2A JSON-RPC Server) | Dedicated IAM Service Account |
| **[`dev-agent`](./dev-agent)** | **Devin** — Lead Platform Developer & SDLC Code Scaffolder | `gemini-3.5-flash-lite` (`LOW`) | **Google Cloud Run** (A2A JSON-RPC Server) | Dedicated IAM Service Account |
| **[`syf-mcp-server`](./syf-mcp-server)** | **Enterprise SDLC FastMCP Server** (GCS Living Workspace, Confluence, Jira, Bitbucket REST APIs) | FastMCP (Streamable HTTP `/mcp`) | **Google Cloud Run** | GCP Agent Identity Auth Manager |

---

## Repository Structure

```text
virtual-product-manager/
├── vpm-agent/                             # Root Orchestrator (Alex) — Vertex AI Agent Runtime
├── finops-agent/                          # Deep Research & FinOps Sub-Agent (Morgan) — Vertex AI Agent Runtime
├── arch-agent/                            # Enterprise Architecture Specialist (Marcus) — Cloud Run A2A
├── dev-agent/                             # Lead Developer & Scaffolder (Devin) — Cloud Run A2A
├── syf-mcp-server/                        # FastMCP Server + Live Atlassian/Bitbucket Client + Seed Data
├── shared_skills/                         # 5 Bespoke SYF Antigravity Skills (SKILL.md + references)
├── scripts/                               # Turnkey Live SDLC Seeding & Provisioning Scripts
├── SYF_VPM_Technical_Design_Document.md   # Comprehensive Technical Design Document (TDD)
├── SYF_VPM_Demo_Storyline_and_Runbook.md  # One-Slide Storyline & Step-by-Step Scenarios (SSD 2.1 & 2.2)
└── A2A_HANDOFF_MANIFEST.md                # Live Endpoints, A2A Agent Cards & SPIFFE Principals
```
