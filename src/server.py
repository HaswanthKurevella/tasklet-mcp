import sqlite3 as sql
from attr import fields
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasklet.db")

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
            enddate DATETIME
        )
    """)
    con.commit()
finally:
    con.close()

mcp = FastMCP()


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
        return {"status": "success", "message": "Task added successfully."}
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
    mcp.run()
