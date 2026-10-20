# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to Signal Studio are documented in this file.

## [1.0.0] - 2026-10-12

### Added
- Conversational DAG validation and repair engine preventing frontend deadlocks from orphan messages (#15189).
- Reasoning isolation parser with configurable `reinject_reasoning` policy to stop `<think>` tag imitation loops (#23339).
- User-scoped tool and MCP server custom header management with secret redaction (#19313).
- Multi-strategy content extraction (fast text, structured markdown, semantic chunker) for chat and knowledge bases (#12619).
- Notes workspace with bidirectional Markdown import/export and chat context referencing (#13464).
- Offline reproducible AI/ML reasoning benchmark runner and evaluation metrics suite.
- OIDC PKCE authentication with Keycloak realm configuration and secure localhost demo mode.
- Responsive React + TypeScript workbench with tree explorer, prompt compiler inspection, and evaluation dashboard.
- Full test suite covering domain algorithms, auth, boundaries, and API workflows.
