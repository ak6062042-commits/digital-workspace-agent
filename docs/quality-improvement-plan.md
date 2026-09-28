# Quality and reliability improvement plan

## Outcome

Make the local workspace agent feel dependable during daily use: accurate state without unnecessary retention, responsive bounded refreshes, clear recoverable failures, and no unexpected destructive action.

## Prioritized plan

| Priority | Problem | Change | Acceptance criterion | Status |
| --- | --- | --- | --- | --- |
| P0 | The local watcher adds diagnostic metadata that the strict API rejects. | Whitelist the outbound snapshot fields. | Opted-in watcher snapshots validate without relaxing the API schema. | Delivered |
| P0 | URLs and window/tab titles can carry credentials or secrets. | Sanitize URL credentials/fragments/sensitive query keys and redact stored context fields. | Stored and returned context contains no token/password values. | Delivered |
| P1 | Overview polling returns unbounded rows every few seconds. | Add indexes, collection caps, counts, duplicate collapse, and five-second non-overlapping dashboard refresh. | Dashboard refresh is bounded and a slow request cannot pile up. | Delivered |
| P1 | Planner context and suggestion collections grow for the life of the process. | Apply explicit in-memory caps while preserving the current context and active suggestions. | Memory use remains bounded during long sessions. | Delivered |
| P1 | Network failures can leave UI controls busy or hide the cause. | Add request timeout messages, action error handling, and `finally` cleanup for forms. | Controls recover after a failed action and show a useful local-backend error. | Delivered |
| P2 | Notification deletion has no second deliberate UI step. | Require a native confirmation before its authenticated delete request. | A mistaken click does not delete a notification. | Delivered |
| P2 | Bulk history deletion and remote/multi-user access need durable confirmation/auditing. | Design a persisted confirmation and audit model before exposing those capabilities. | No implementation in this local-only iteration. | Deferred |

## Design constraints

- Preserve `State Estimator -> Planner -> Policy -> Executor -> Tool`.
- Keep collection, search, and execution opt-in.
- Maintain API response compatibility for current dashboard, widget, extension, and Word clients.
- Prefer small reversible improvements with tests over speculative integrations.

## Verification

1. Run the Python unit suite and compile check.
2. Build the Vite frontend.
3. Check the watcher payload has only documented snapshot fields.
4. Verify URL sanitization, snapshot validation, bounded planner memory, and failed-form recovery paths.
