import sqlite3 as sql
from mcp.server.fastmcp import FastMCP
from datetime import datetime

con = sql.connect("tasklet.db")
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

# Initialize FastMCP server
mcp = FastMCP()


@mcp.tool()
def add_task(
    task: str, description: str = None, start: datetime = None, end: datetime = None
):
    """Add a new task to the database."""
    con = sql.connect("tasklet.db")
    try:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO tasks (task, description, start, end)
            VALUES (?, ?, ?, ?)
        """,
            (task, description, start, end),
        )
        con.commit()
        return {"status": "success", "message": "Task added successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        con.close()


if __name__ == "__main__":
    mcp.run()
