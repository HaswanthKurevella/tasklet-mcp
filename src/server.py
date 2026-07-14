import sqlite3 as sql
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
            start DATETIME,
            lodgedon DATETIME DEFAULT CURRENT_TIMESTAMP,
            end DATETIME
        )
    """)
    con.commit()
finally:
    con.close()

mcp = FastMCP()


@mcp.tool()
def add_task(
    task: str, description: str = None, start: datetime = None, end: datetime = None
):
    """Add a new task to the tasklet."""
    con = sql.connect(DB_PATH)
    try:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO tasks (task, description, start, end)
            VALUES (?, ?, ?, ?)
            """,
            (
                task,
                description,
                (
                    start.isoformat() if start else None
                ),  # datetime -> string fix from earlier
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
    """ Lists all the tasks present in database """
    con = sql.connect(DB_PATH)
    try:
        cur = con.cursor()
        res = cur.execute(
            """
            SELECT * FROM tasks
            """
        )
        con.commit()
        return {"status": "success", "message": res.fetchall()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        con.close()
    

if __name__ == "__main__":
    mcp.run()
