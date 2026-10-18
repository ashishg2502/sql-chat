import os
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env
load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are an expert SQL assistant specializing in SQLite.
Your task is to generate a single, valid, and efficient SQLite SELECT query based on the provided database schema and user question.

Strict Rules:
1. Return ONLY the raw SQL query. Do NOT wrap it in markdown code blocks like ```sql ... ```.
2. Generate ONLY SELECT queries. Do NOT produce INSERT, UPDATE, DELETE, or DROP statements.
3. Match column names and table names exactly as shown in the provided schema.
4. If the question asks for aggregations or specific filters, write the query accordingly.
5. Do NOT include explanations, conversational text, or comments in your response.
"""


def generate_sql(messages: list[dict]) -> str:
    """Send conversation context to Gemini and extract the generated SQL query."""
    contents = []
    for msg in messages:
        contents.append(f"{msg['role'].upper()}: {msg['content']}")

    full_prompt = "\n\n".join(contents)

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
        ),
    )

    raw_sql = response.text.strip()

    # Clean markdown fences if present
    clean_sql = re.sub(r"^```(?:sql)?\s*", "", raw_sql, flags=re.IGNORECASE)
    clean_sql = re.sub(r"\s*```$", "", clean_sql)

    return clean_sql.strip()