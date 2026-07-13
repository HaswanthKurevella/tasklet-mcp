import sqlite3 as sql
con = sql.connect("tasklet.db")
cur = con.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS tasks()
""")
