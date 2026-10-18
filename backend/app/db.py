import re
import sqlite3
import time
import uuid
from pathlib import Path
import pandas as pd

# Directory where uploaded CSVs will be saved as SQLite database files
DB_DIR = Path("data/dbs")
DB_DIR.mkdir(parents=True, exist_ok=True)


def clean_name(name: str) -> str:
    """Sanitize table and column names to prevent SQL injection or formatting issues."""
    return re.sub(r"\W+", "_", name.strip().lower()).strip("_") or "col"


def csv_to_db(file_obj, filename: str) -> str:
    """Read an uploaded CSV file, sanitize headers, and save as a local SQLite DB file."""
    df = pd.read_csv(file_obj)
    df.columns = [clean_name(c) for c in df.columns]
    table_name = clean_name(Path(filename).stem)
    
    # Generate a unique 12-character ID for this database file
    db_id = uuid.uuid4().hex[:12]
    db_path = DB_DIR / f"{db_id}.db"
    
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, index=False, if_exists="replace")
    conn.close()
    
    return db_id


def open_readonly(db_id: str) -> sqlite3.Connection:
    """Safely open an existing SQLite database file in read-only mode."""
    # Validate db_id format to prevent path traversal attacks
    if not re.fullmatch(r"[a-f0-9]{12}", db_id):
        raise FileNotFoundError("Invalid database identifier format.")
        
    path = (DB_DIR / f"{db_id}.db").resolve()
    if not path.exists():
        raise FileNotFoundError("Database file not found.")
        
    # Connect using SQLite's read-only URI mode
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def get_schema(conn: sqlite3.Connection, sample_rows: int = 3) -> str:
    """Extract table structures and sample rows to send to the LLM context."""
    schema_parts = []
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    
    for (table,) in tables:
        cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        col_str = ", ".join(f"{c[1]} {c[2]}" for c in cols)
        
        rows = conn.execute(f'SELECT * FROM "{table}" LIMIT {sample_rows}').fetchall()
        schema_parts.append(f"Table: {table}\nColumns: ({col_str})\nSample Data ({sample_rows} rows): {rows}")
        
    return "\n\n".join(schema_parts)


def run_query(conn: sqlite3.Connection, sql: str, max_rows: int = 500, timeout: float = 5.0):
    """Run a SELECT query with a row count limit and execution timeout interrupt."""
    start_time = time.time()
    
    # Abort execution if query runs longer than timeout (prevents infinite loops)
    conn.set_progress_handler(lambda: 1 if time.time() - start_time > timeout else 0, 10000)
    
    cur = conn.execute(sql)
    columns = [desc[0] for desc in cur.description] if cur.description else []
    rows = cur.fetchmany(max_rows)
    
    return columns, rows