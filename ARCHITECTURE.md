# ArmorScan AI - Architecture Documentation

This document provides an in-depth explanation of the `backend` and `agents` directories, the LangGraph workflow, the specific agent roles, and how ArmorIQ is utilized as the safety and policy engine.

---

## 1. Directory Overview

### `backend/`
The `backend` directory houses the REST API built with **FastAPI**. It acts as the gateway between the frontend application and the core scanning engines.
- **API Endpoints (`app/api/`)**: Exposes REST routes (e.g., `/reports/{scan_id}/pdf`, `/scans`, `/targets`) that the Next.js frontend calls.
- **Services (`app/services/`)**: Contains business logic bridges. For example, `risk.py` handles PDF generation, markdown reports, and acts as the interface to the underlying agent graph.
- **Database & Auth**: Connects to the primary database using SQLAlchemy/asyncpg and manages user authentication (JWTs, OAuth).
- **Execution Environment**: Runs via `uvicorn` and manages background scan jobs (often via Celery or asyncio tasks) to prevent blocking the HTTP event loop during long-running agent workflows.

### `agents/`
The `agents` directory (specifically `agents/armorscan/`) contains the core "brain" of the application. It uses a **LangGraph** State Graph to orchestrate a sophisticated, multi-agent vulnerability scanning pipeline.
- It operates on a `ScanState` dictionary that accumulates evidence, findings, and observations as it moves sequentially through a pipeline of specialized agents.
- It is designed to be highly modular, with specific functions mapping out attack surfaces, normalizing data, using LLMs for analysis, and performing safe exploit verifications.

---

## 2. The LangGraph Workflow (Agent Roles)

The scanning process follows a deterministic pipeline defined in `agents/armorscan/graph.py`. Each node in the graph represents a specific agent or system phase:

1. **`planner_node`**: Prepares the governed scan plan. It determines the phases, allowed actions, and boundaries for the scan.
2. **`recon_node`**: Performs passive reconnaissance (e.g., DNS, subdomains, passive HTTP mapping) without sending aggressive payloads.
3. **`browser_workflow_agent`**: A specialist agent that analyzes the target through a headless browser. It extracts JavaScript sources, maps authenticated workflows, and identifies user input forms (like login or file upload panels).
4. **`api_discovery_agent`**: Analyzes the extracted routes and HTTP observations to map the API surface. It specifically targets REST/GraphQL endpoints.
5. **`repo_sast_agent`**: If the target is a GitHub repository, this agent inventories the source code, extracting frameworks, routes, and potential hardcoded secrets using Static Application Security Testing (SAST) methodologies.
6. **`dependency_supply_chain_agent`**: Also active for repository scans. It inventories software dependencies (e.g., `package.json`, `requirements.txt`) and Infrastructure-as-Code (IaC) files to identify supply chain risks.
7. **`scanner_registry_agent`**: Prepares a capability matrix of integrated scanning engines (e.g., DAST tools, nuclei) based on the scan type.
8. **`engines_node`**: Actually executes the third-party or internal scanning engines, appending raw observations, findings, and errors to the state.
9. **`evidence_normalization_agent`**: Consolidates and standardizes the disparate evidence gathered from the browser, API, repo, and scanner outputs into a unified format.
10. **`analysis_node`**: Uses an LLM (specifically Groq) as an analysis agent. It takes the normalized evidence and drafts defensive, safe validation ideas and candidate vulnerabilities (OWASP-style) formatted as JSON.
11. **`exploit_node`**: Safely validates the drafted findings. If the LLM drafted a payload, this node performs a harmless HTTP probe to confirm the vulnerability. **(See ArmorIQ section below)**.
12. **`correlation_agent`**: Cross-references findings with the normalized evidence. It boosts the confidence score of a finding if multiple distinct sources (e.g., SAST and DAST) observed the same vulnerability.
13. **`retest_agent`**: Prepares a safe retest plan for the validated findings, outlining how they can be re-verified once a fix is applied.
14. **`reporter_node`**: Synthesizes the final vulnerability report, converting the state into a comprehensive JSON (which the backend later uses for PDF generation).

---

## 3. ArmorIQ: The Safety & Policy Engine

A critical concern in autonomous agentic scanning is ensuring that agents do not perform destructive actions (e.g., dropping databases, causing DoS, or accessing out-of-scope targets). **ArmorIQ** solves this problem.

### Where is ArmorIQ Used?
ArmorIQ is implemented primarily in `agents/armorscan/policy.py` and is invoked directly by the `exploit_node` (and during reconnaissance/API discovery).

### How it Works:
1. **The Intent Token**: Before a scan starts, an `armoriq_token` and an `intent_plan` are generated. This plan mathematically signs the allowed actions (e.g., `["http.get"]`), the allowed hosts, and the scan expiration time.
2. **Action Evaluation**: When the `exploit_node` attempts to test an LLM-generated payload against a URL, it calls `evaluate_agent_action()`.
3. **Strict Validation Constraints**: 
   - It checks if the `armoriq_token` is valid and the plan is not expired.
   - It checks if the target URL matches the `allowed_hosts` defined in the intent plan (preventing the agent from pivoting to internal network IPs like `169.254.169.254`).
   - It scans the payload against `BLOCKED_PAYLOAD_MARKERS` (e.g., `rm -rf`, `powershell`, `/etc/passwd`) to prevent the agent from executing dangerous or destructive payloads.
4. **Enforcement**: If `evaluate_agent_action` returns `allowed: False`, the `exploit_node` blocks the HTTP request entirely and logs a policy violation.

In summary, ArmorIQ acts as the **sandbox boundary** that keeps the LLM and the scanning agents perfectly aligned with the user's authorized scope and safety constraints.
