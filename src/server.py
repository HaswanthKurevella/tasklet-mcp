import sqlite3 as sql
from mcp.server.fastmcp import FastMCP
from datetime import datetime, timezone
import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCOPES = ["https://www.googleapis.com/auth/tasks"]
TOKEN_FILE = os.path.join(BASE_DIR, "credentials", "token.json")
TASKLIST_FILE = os.path.join(BASE_DIR, "credentials", "tasklet_list.json")
DB_PATH = os.path.join(BASE_DIR, "src", "tasklet.db")


def get_tasks_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("tasks", "v1", credentials=creds)


from googleapiclient.errors import HttpError


def get_or_create_tasklist(service):
    if os.path.exists(TASKLIST_FILE):
        try:
            with open(TASKLIST_FILE, "r") as f:
                data = json.load(f)
                cached_id = data.get("id")
            if cached_id:
                try:
                    service.tasklists().get(tasklist=cached_id).execute()
                    return cached_id
                except HttpError as e:
                    if e.resp.status == 404:
                        pass
                    else:
                        raise
        except json.JSONDecodeError, KeyError:
            pass

    result = service.tasklists().insert(body={"title": "Tasklet"}).execute()
    list_id = result["id"]

    with open(TASKLIST_FILE, "w") as f:
        json.dump({"id": list_id}, f)

    return list_id


con = sql.connect(DB_PATH)
try:
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            task TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','active','done')),
            createdtime DATETIME DEFAULT CURRENT_TIMESTAMP,
            updatedtime DATETIME DEFAULT CURRENT_TIMESTAMP,
            enddate DATETIME,
            google_task_id TEXT
        )
    """)
    con.commit()
finally:
    con.close()

mcp = FastMCP()


def _to_google_due(end: datetime) -> str:
    """Convert a (possibly naive) datetime into an RFC3339 UTC string for Google Tasks 'due'."""
    if end.tzinfo is None:
        end = end.astimezone()  # treat naive datetime as local wall-clock time
    return end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@mcp.tool()
def add_task(task: str, description: str = None, end: datetime = None):
    """Add a new task to the tasklet."""
    con = sql.connect(DB_PATH)
    try:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO tasks (task, description, createdtime, updatedtime, enddate)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                task,
                description,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                end.isoformat() if end else None,
            ),
        )
        con.commit()
        task_id = cur.lastrowid

        google_task_id = None
        try:
            service = get_tasks_service()
            tasklist_id = get_or_create_tasklist(service)
            task_body = {
                "title": task,
                "notes": description or "",
            }
            if end:
                task_body["due"] = _to_google_due(end)
            created_task = (
                service.tasks().insert(tasklist=tasklist_id, body=task_body).execute()
            )
            google_task_id = created_task.get("id")

            cur.execute(
                "UPDATE tasks SET google_task_id = ? WHERE id = ?",
                (google_task_id, task_id),
            )
            con.commit()
        except Exception as sync_error:
            print(f"Google Tasks sync failed for task {task_id}: {sync_error}")

        return {
            "status": "success",
            "message": "Task added successfully.",
            "google_synced": google_task_id is not None,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        con.close()


@mcp.tool()
def list_tasks():
    """Lists all the tasks present in database"""
    con = sql.connect(DB_PATH)
    try:
        cur = con.cursor()
        res = cur.execute("""
            SELECT * FROM tasks
            """)
        con.commit()
        cols = [
            "id",
            "task",
            "description",
            "status",
            "createdtime",
            "updatedtime",
            "enddate",
            "google_task_id",
        ]
        rows = res.fetchall()
        data = [dict(zip(cols, row)) for row in rows]
        return {"status": "success", "message": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        con.close()


@mcp.tool()
def update_task(
    task_id: int,
    task: str = None,
    description: str = None,
    status: str = None,
    end: datetime = None,
):
    """Update one or more fields of an existing task. Only provided fields are changed."""
    con = sql.connect(DB_PATH)
    try:
        cur = con.cursor()
        fields_to_update = []
        values = []
        if task is not None:
            fields_to_update.append("task = ?")
            values.append(task)
        if description is not None:
            fields_to_update.append("description = ?")
            values.append(description)
        if status is not None:
            fields_to_update.append("status = ?")
            values.append(status)
        if end is not None:
            fields_to_update.append("enddate = ?")
            values.append(end.isoformat())
        if not fields_to_update:
            return {"status": "error", "message": "No fields to update."}
        else:
            fields_to_update.append("updatedtime = ?")
            values.append(datetime.now().isoformat())
        values.append(task_id)
        set_clause = ", ".join(fields_to_update)
        query = f"UPDATE tasks SET {set_clause} WHERE id = ?"
        cur.execute(query, values)
        con.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No task with id {task_id}."}
        return {"status": "success", "message": "Task updated successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        con.close()


@mcp.tool()
def delete_task(task_id: int):
    """Delete a task by id."""
    con = sql.connect(DB_PATH)
    try:
        cur = con.cursor()
        cur.execute("DELETE FROM tasks WHERE id = ?", [task_id])
        con.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No task with id {task_id}."}
        return {"status": "success", "message": "Task deleted successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        con.close()


@mcp.prompt()
def plan_my_day():
    """Generate a prompt that builds a prioritzed and scheduled plan for the day based on the tasks in the database."""
    return (
        "call the list_tasks() tool to get all the tasks in the database. "
        "Identify the tasks that are pending or active and have an end date of today or earlier. "
        "Prioritize these tasks based on their end dates and any other relevant factors. "
        "Create a schedule for the day that allocates time for each task, ensuring that higher "
        "priority tasks are scheduled earlier in the day. Return the schedule in a clear and organized format."
    )


if __name__ == "__main__":
    service = get_tasks_service()
    tasklist_id = get_or_create_tasklist(service)
    print("Tasks service created successfully:", service)
    print("Tasklet list id:", tasklist_id)
    mcp.run()
