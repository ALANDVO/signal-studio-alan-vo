# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

core-engine-and-workbench

## Roadmap

### core-engine-and-workbench — Chat Tree DAG Integrity & Reasoning Isolation Engine

Status: done

Acceptance:
- Detects and repairs orphan messages in conversation tree structures (#15189)
- Extracts and isolates <think> reasoning tags, preventing imitation loops in multi-turn prompts (#23339)
- Provides user-scoped MCP/tool custom headers (#19313)
- Supports multi-strategy document chunking (#12619) and notes (#13464)
- Includes reproducible AI/ML benchmark evaluation suite

Implementation: `backend/app/main.py`, `backend/app/services/tree_validator.py`, `backend/app/services/reasoning_filter.py`, `backend/app/services/tool_proxy.py`, `backend/app/services/content_extractor.py`, `backend/app/services/eval_runner.py`, `frontend/src/App.tsx`

Tests: `backend/tests/test_tree_validator.py`, `backend/tests/test_reasoning_filter.py`, `backend/tests/test_content_extractor.py`, `backend/tests/test_tool_proxy.py`, `backend/tests/test_eval_runner.py`, `backend/tests/test_auth_and_security.py`, `backend/tests/test_api_workflows.py`

### native-multimodal-audio-video — Direct Multimodal Audio and Video Streaming (#23357)

Status: planned

Acceptance:
- Stream native audio and video to multimodal vision/speech models without mandatory intermediate STT transcription

### external-storage-connectors — External Cloud Storage Connectors (#5872)

Status: planned

Acceptance:
- Ingest documents directly from Google Drive, NextCloud, Dropbox, and OneDrive data sources

