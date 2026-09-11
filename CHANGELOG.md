# Changelog

## [0.3.1] - 2026-09-11
### Fixed
- create_tickets_for_repo() was entirely missing from ticket_creator.py
  (corrupted, unreachable dead code from a bad merge). issueloop.create_tickets()
  raised AttributeError on every call. Rebuilt the file.

## [0.3.0] - 2026-09-10
### Fixed
- Published wheel actually matches `main` this time — `0.2.1` was a
  metadata-only republish and never re-cut from the `0.2.0` commit that
  added the full API. Verified by downloading `0.2.1` from PyPI and
  diffing its `__all__` against `main`: published had 10 functions,
  `main` has 49.
- Added a version-tag-triggered GitHub Actions publish workflow using
  PyPI Trusted Publishing (OIDC) so this can't silently drift again —
  no long-lived token stored in the repo.

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