# Word Writing Assistant

This Office task-pane add-in analyzes **only text selected by the user**. It never reads a document in the background.

1. Start the backend: `scripts\run_backend.bat`.
2. In Word for Windows, open **Home → Add-ins → More Add-ins → My Add-ins → Upload My Add-in**.
3. Choose `manifest.xml` in this directory and open the Workspace Writing Assistant task pane.
4. Paste `API_TOKEN` from the local `.env` into the add-in once.
5. Select text in Word and click **Analyze selected text**. The pane displays the local rewrite plus related-document searches; selecting a search opens its query in Chrome.

After a code update, close and reopen the task pane (or remove and re-add the development add-in) before testing so Word is not using its cached page.

The add-in is local development software served from `http://localhost:8000/word-addin`. Office may warn about an HTTP localhost add-in. For organization-wide deployment or Word on the web, host the same files over trusted HTTPS and change the manifest URLs before sideloading. Microsoft documents localhost sideloading and recommends HTTPS for deployed add-ins. [Microsoft Learn](https://learn.microsoft.com/en-us/office/dev/add-ins/testing/sideload-office-add-ins-for-testing)
