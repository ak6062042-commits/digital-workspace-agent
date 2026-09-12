# Manual verification runbook

Run setup and start the backend/frontend before this checklist. The dashboard needs `VITE_API_TOKEN` from the generated `.env`.

1. Open the dashboard and confirm the privacy card reports typing capture disabled.
2. Create a task, move it to `ongoing`, then mark it `done`.
3. Send: `What was I working on?` and `What changed while I was away?`.
4. Send: `Open VS Code`. Confirm that only an allowlisted application can launch.
5. Send: `Research PPO reward shaping`. Confirm that research is planned/executed without sending workspace document text automatically.
6. Paste non-sensitive sample text into Writing Assist and run an operation. Confirm a suggestion appears; mark it reviewed.
7. Use the extension popup: set the token, keep sync disabled, select a paragraph, then choose Analyze selected text. Confirm no result exists until the button is clicked.
8. Run `scripts/test.*` and `cd frontend && npm run build`.

Security smoke checks:

- Calling an API endpoint without `X-Workspace-Token` returns `401`.
- A chat request such as `Open powershell & whoami` does not create a desktop launch plan.
- Raw HTML in a chat message is displayed without executing in the dashboard.
