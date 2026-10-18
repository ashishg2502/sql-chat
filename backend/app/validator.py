import sqlglot
from sqlglot import exp


class UnsafeSQLError(Exception):
    """Custom exception raised when a query fails security checks."""
    pass


def validate_sql(sql: str) -> str:
    """Parse SQL query with sqlglot and verify it contains only safe SELECT operations."""
    cleaned_sql = sql.strip().rstrip(";")
    
    try:
        # Parse SQL string into an Abstract Syntax Tree (AST) using SQLite dialect
        parsed_statements = sqlglot.parse(cleaned_sql, read="sqlite")
    except Exception as e:
        raise UnsafeSQLError(f"SQL syntax error: {str(e)}")
        
    if not parsed_statements or len(parsed_statements) > 1:
        raise UnsafeSQLError("Only single SQL statements are allowed.")
        
    statement = parsed_statements[0]
    
    # Ensure statement is strictly a SELECT statement
    if not isinstance(statement, exp.Select):
        raise UnsafeSQLError("Only SELECT queries are permitted.")
        
    # Walk through AST nodes to detect dangerous commands (DROP, DELETE, UPDATE, INSERT, ALTER)
    forbidden_types = (
        exp.Drop,
        exp.Delete,
        exp.Update,
        exp.Insert,
        exp.Alter,
        exp.Create,
    )
    
    for node in statement.walk():
        if isinstance(node, forbidden_types):
            raise UnsafeSQLError(f"Forbidden operation detected: {type(node).__name__}")
            
    return cleaned_sql