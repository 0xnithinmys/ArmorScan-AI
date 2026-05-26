# ArmorScan AI — Agents Package
#
# Multi-agent AI system built on LangGraph.
# Phase 4 implementation lives in this package.
#
# Structure:
#   armorscan/
#     graph.py          — LangGraph state machine wiring all agents
#     state.py          — Shared ScanState TypedDict
#     agents/
#       recon.py        — Reconnaissance Agent
#       analysis.py     — Vulnerability Analysis Agent
#       exploit.py      — Exploitation & Validation Agent
#       reporter.py     — Reporting & Triage Agent
#     tools/
#       playwright_tools.py  — Browser automation tool wrappers
#       nuclei_tools.py      — Nuclei scanner tool wrappers
#       http_tools.py        — Raw HTTP fuzzing tools
