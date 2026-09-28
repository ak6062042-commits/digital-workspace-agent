# Remediation plan

## Goal

Keep the Digital Workspace Agent useful without turning local observations, model output, browser content, or voice transcription into a computer-control path. The execution order is security, architecture, reliability, functionality, then polish.

## Audit method

1. Map each input source, persistence boundary, network boundary, and desktop side effect.
2. Trace every request through State Estimator, Planner, Executor, and tool implementation.
3. Test the fail-closed cases: missing/weak token, unsafe CORS, unapproved application, malformed request, unavailable backend, and untrusted rendered content.
4. Review the client surfaces separately because an XSS issue can reuse the local API token.

## Findings and disposition

| Priority | Finding | Resolution | Evidence |
| --- | --- | --- | --- |
| P0 | Chat Markdown reached an HTML sink without a dedicated sanitizer. | Sanitize `marked` output with DOMPurify immediately before rendering. | Frontend build and Markdown smoke test. |
| P0 | Voice recognition auto-sent a detected command after three seconds. | Stage voice text in the composer; require the existing Send action. | Source inspection and manual UI runbook. |
| P0 | The watcher could write directly to SQLite when the API failed. | Remove the direct-write fallback and default the legacy setting to false. | Watcher tests and source search. |
| P1 | CORS and Host settings could be weakened through configuration, and a short token passed the old check. | Enforce explicit loopback CORS origins, Host allowlist, and a 32-character token minimum at startup. | Unit tests for configuration validation. |
| P1 | Request models silently ignored unexpected fields. | Use Pydantic `extra=forbid` for all API request models. | Request-model test. |
| P2 | Current data deletion endpoints execute after a direct authenticated UI action. | Keep this behavior for now; add a product-level confirmation workflow before exposing deletion to any non-local or automation client. | Follow-up design review. |

## Delivered sequence

1. Harden inbound transport and configuration.
2. Protect browser rendering and voice-control authority.
3. Preserve the State -> Planner -> Executor boundary by removing the persistence bypass.
4. Add regression tests and run backend/frontend verification.
5. Revisit P2 only with a concrete UX for deletion confirmation and durable confirmation storage.

## Non-goals in this change

- Remote or multi-user access. That requires a separate authentication, secret-distribution, TLS, audit-log, and authorization design.
- Arbitrary desktop control, shell access, external LLM processing, or background page scraping.
