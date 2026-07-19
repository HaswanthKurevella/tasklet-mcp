# tasklet

A lightweight MCP server for managing tasks — built with FastMCP and SQLite, with two-way-capable sync into **Google Tasks**.

Tasks added, updated, or listed through the MCP server are stored locally in SQLite. When a task is added, it's also pushed to a dedicated **"Tasklet"** list in your Google Tasks account, so it's visible outside the MCP client too (e.g. in the Google Tasks app, or Gmail's sidebar).

## How it works

- SQLite is the source of truth. Google Tasks is treated as an addon layer on top of it.
- Every task row keeps a `google_task_id` column, linking it to its corresponding Task in Google.
- If the Google Tasks sync fails for any reason (expired token, no internet, API hiccup), the task still saves locally — sync failures never block the core task operation.
- Auth uses OAuth2 with a locally stored refresh token, so you authenticate once and the server silently refreshes access after that — no repeated logins.

## Prerequisites

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) installed
- A Google account

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Create Google Cloud credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project (or use an existing one).
2. **APIs & Services → Library** → search **"Google Tasks API"** → click **Enable**.
3. **APIs & Services → OAuth consent screen**:
   - User type: **External**
   - Fill in app name, your email, save
   - Under **Scopes**, add `https://www.googleapis.com/auth/tasks`
   - Under **Test users**, add your own Google account email (required while the app is unpublished)
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app** — this matters, don't pick "Web application." Desktop app credentials are the type Google expects to be used with a local loopback redirect (`http://localhost:<random-port>`), which is what the one-time login flow below relies on. A Web application credential will reject the redirect with a `redirect_uri_mismatch` error.
   - Create, then download the JSON.
5. Save the downloaded file as:

   ```
   credentials/client_secret.json
   ```

### 3. Run the one-time login

```bash
uv run python src/auth_setup.py
```

This opens your browser to Google's consent screen. Log in and click Allow. On success, it writes `credentials/token.json`, which contains a long-lived refresh token — the server reads this file on every startup and refreshes it silently as needed. You should only need to do this once, unless you delete `token.json` or revoke access from your Google account.

### 4. Run the server

```bash
uv run python src/server.py
```

On first run, this also creates a dedicated **"Tasklet"** list in your Google Tasks account (separate from your default list, so synced tasks don't mix with anything you manage manually). The list's id is cached in `credentials/tasklet_list.json`.

## MCP tools

| Tool | Description |
|---|---|
| `add_task(task, description=None, end=None)` | Adds a task to SQLite and pushes it to your Google Tasks "Tasklet" list. |
| `list_tasks()` | Lists all tasks from the local database. |
| `update_task(task_id, task=None, description=None, status=None, end=None)` | Updates one or more fields of an existing task (local only, does not currently sync updates to Google). |
| `delete_task(task_id)` | Deletes a task by id (local only, does not currently sync deletions to Google). |

There's also an MCP prompt, `plan_my_day`, which builds a prioritized schedule from tasks due today or earlier.

## Using with an MCP client (e.g. Claude Desktop / Claude Code)

Point your client at:

```json
{
  "servers": {
    "tasklet": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "src/server.py"]
    }
  }
}
```

## Known limitations / roadmap

- **One direction only right now**: `add_task` pushes to Google Tasks, but `update_task` and `delete_task` don't yet. Editing or deleting a task locally won't be reflected in Google Tasks.
- **No pull sync**: changes made directly in the Google Tasks app (marking complete, editing, deleting) aren't pulled back into the local SQLite database. Full two-way sync (via polling with sync tokens, or push notifications) is planned but not yet implemented.
- **Single account**: this is built for one personal Google account, authenticated once via the local OAuth flow — not designed for multi-user/multi-tenant use.

## Security notes

- `credentials/` is gitignored — never commit `client_secret.json` or `token.json`. The latter contains a refresh token that grants standing access to your Google Tasks account.
- If you ever suspect either file has leaked, revoke access immediately at [myaccount.google.com/permissions](https://myaccount.google.com/permissions), then rerun `auth_setup.py` to get a fresh token.
