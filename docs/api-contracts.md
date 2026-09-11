# Digital Workspace Agent — API Contracts

This document specifies the REST API contracts between:
- **Track C (Systems/Integration)**: Local agent & browser extension posting state snapshots.
- **Track A (AI/Backend)**: Coordinator and sub-agents reading state and managing tasks.
- **Track B (Frontend/Product)**: React/Vite UI fetching tasks, status, and chatting with the agent.

Base URL: `http://localhost:8000`

---

## 1. System State Endpoints

### `POST /api/snapshot`
Ingest a workspace state snapshot from the local agent or browser companion.

- **Request Body**: (JSON, conforms to `shared/schemas/state_snapshot.json`)
  ```json
  {
    "active_app": "Google Chrome",
    "active_window_title": "FastAPI Documentation - Overview",
    "browser_url": "https://fastapi.tiangolo.com/",
    "browser_tab_title": "FastAPI Documentation - Overview",
    "captured_at": "2026-09-11T05:58:14.865986+00:00",
    "metadata": {
      "source": "local-agent",
      "os_platform": "darwin"
    }
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "status": "success",
    "snapshot": {
      "id": 14,
      "active_app": "Google Chrome",
      "active_window_title": "FastAPI Documentation - Overview",
      "browser_url": "https://fastapi.tiangolo.com/",
      "browser_tab_title": "FastAPI Documentation - Overview",
      "captured_at": "2026-09-11T05:58:14.865986"
    }
  }
  ```

---

### `GET /api/snapshot/latest`
Retrieve the most recent OS/browser state snapshot. Used by the Coordinator to inject real-time context into agent prompts and by the Frontend status bar.

- **Response**: `200 OK`
  ```json
  {
    "id": 14,
    "active_app": "Google Chrome",
    "active_window_title": "FastAPI Documentation - Overview",
    "browser_url": "https://fastapi.tiangolo.com/",
    "browser_tab_title": "FastAPI Documentation - Overview",
    "captured_at": "2026-09-11T05:58:14.865986"
  }
  ```
  *(Returns `null` if no snapshot has been captured yet).*

---

### `POST /api/browser/open`
Launch or navigate the desktop browser to a specific URL.

- **Request Body**:
  ```json
  {
    "url": "https://www.google.com/search?q=railway+vs+vercel"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "url": "https://www.google.com/search?q=railway+vs+vercel"
  }
  ```

---

## 2. Tasks Endpoints

### `GET /api/tasks`
List all workspace tasks.

- **Query Parameters**:
  - `done` (optional, boolean): Filter by completed status (`true` or `false`).
- **Response**: `200 OK`
  ```json
  [
    {
      "id": 1,
      "title": "Research deployment options",
      "description": "Compare Vercel vs Railway for frontend/backend hosting",
      "done": false,
      "created_at": "2026-09-11T02:48:02.884692",
      "due_at": null
    }
  ]
  ```

---

### `POST /api/tasks`
Create a new task (called by Task Agent or user via UI).

- **Request Body**:
  ```json
  {
    "title": "Configure staging database",
    "description": "Provision PostgreSQL on Railway",
    "due_at": "2026-09-15T18:00:00Z"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "id": 2,
    "title": "Configure staging database",
    "description": "Provision PostgreSQL on Railway",
    "done": false,
    "created_at": "2026-09-11T06:00:00",
    "due_at": "2026-09-15T18:00:00"
  }
  ```

---

### `PATCH /api/tasks/{task_id}`
Toggle or update task properties.

- **Request Body**:
  ```json
  {
    "done": true
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "id": 2,
    "done": true
  }
  ```

---

## 3. Coordinator & AI Endpoints

### `POST /api/chat`
Send user instructions to the coordinator agent.

- **Request Body**: (conforms to `shared/schemas/agent_request.json`)
  ```json
  {
    "message": "What was I working on before this meeting?",
    "session_id": "session-xyz",
    "include_state": true
  }
  ```
- **Response**: `200 OK` (conforms to `shared/schemas/agent_response.json`)
  ```json
  {
    "response": "You were reviewing the FastAPI documentation and inspecting your local Docker Compose setup in Terminal.",
    "routed_agent": "state_agent",
    "tasks_created": [],
    "state_snapshot": {
      "id": 14,
      "active_app": "Google Chrome",
      "active_window_title": "FastAPI Documentation - Overview",
      "browser_url": "https://fastapi.tiangolo.com/",
      "browser_tab_title": "FastAPI Documentation - Overview",
      "captured_at": "2026-09-11T05:58:14.865986"
    },
    "timestamp": "2026-09-11T06:00:02.123456Z"
  }
  ```
