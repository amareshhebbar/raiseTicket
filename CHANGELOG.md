# Changelog

## [0.2.1] - 2026-08-04
### Fixed
- PyPI metadata: switched to SPDX license expression, removed deprecated License classifier
### Added
- keywords/classifiers for PyPI discoverability

## [0.2.0] - 2026-08-03
### Added
- Full ~45-function API (bug query, lifecycle, fix-apply, live monitoring, LLM/token tracking, DB maintenance)
- Multi-provider LLM fallback
- live_monitor.py (spawn-and-own or tail-log modes)
- Go client package, extended npm client (5 → 49 methods)
- RPC dispatcher + CORS support in server.py
### Fixed
- Every Phase 1 stabilization bug (see PR history)