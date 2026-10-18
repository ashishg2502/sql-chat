import os
import sqlite3
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import llm
from app.db import csv_to_db, get_schema, open_readonly, run_query
from app.validator import UnsafeSQLError, validate_sql

app = FastAPI(title="Text-to-SQL API")

# Configure CORS to allow requests from local frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB max file size limit


class AskRequest(BaseModel):
    db_id: str
    question: str = Field(min_length=3, max_length=500)


@app.get("/health")
def health():
    """Health check endpoint to verify backend status."""
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile):
    """Endpoint to upload a CSV file and convert it into a sandboxed SQLite database."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB allowed).")

    file.file.seek(0)

    try:
        db_id = csv_to_db(file.file, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV file: {str(e)}")

    conn = open_readonly(db_id)
    schema = get_schema(conn)
    conn.close()

    return {"db_id": db_id, "schema": schema}


@app.post("/ask")
def ask(req: AskRequest):
    """Endpoint that takes a natural language question, generates SQL, validates, executes, and retries on errors."""
    try:
        conn = open_readonly(req.db_id)
    except (FileNotFoundError, sqlite3.Error):
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload again.")

    schema = get_schema(conn)
    messages = [
        {
            "role": "user",
            "content": f"Database Schema:\n{schema}\n\nQuestion: {req.question}",
        }
    ]

    last_error = None

    # Self-correction retry loop (up to 3 attempts)
    for attempt in range(1, 4):
        try:
            sql = llm.generate_sql(messages)
            safe_sql = validate_sql(sql)
            columns, rows = run_query(conn, safe_sql)
            conn.close()
            
            return {
                "sql": safe_sql,
                "columns": columns,
                "rows": rows,
                "attempts": attempt,
            }
        except (UnsafeSQLError, sqlite3.Error) as e:
            last_error = str(e)
            messages.extend([
                {"role": "assistant", "content": sql if 'sql' in locals() else ""},
                {"role": "user", "content": f"That failed with error: {e}. Please fix the query and return a valid SELECT query."},
            ])

    conn.close()
    raise HTTPException(status_code=422, detail=f"Could not produce a valid query after 3 attempts. Last error: {last_error}")