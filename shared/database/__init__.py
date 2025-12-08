"""
Database Connection and Operations

Handles connection to Redshift database and data operations.
Shared across all carrier calculators.
"""

import polars as pl
import pandas as pd
import redshift_connector
from pathlib import Path
from typing import Union, Literal, Optional


# Database connection parameters
HOST = "bi.c5lrs7vtwcpl.eu-central-1.redshift.amazonaws.com"
PORT = 5439
DBNAME = "bi_stage_dev"
USER = "tcg_nfe"


# Global connection object
_connection: Optional[redshift_connector.Connection] = None


# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

def _read_password() -> str:
    """
    Read password from pass.txt file in the database directory.

    Returns:
        str: The database password

    Raises:
        RuntimeError: If password file is not found or is empty
    """
    path = Path(__file__).parent / "pass.txt"

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                val = line.strip()
                if val:
                    return val

    raise RuntimeError(
        f"Password not found. Please create 'pass.txt' in {path.parent}"
    )


def get_connection(force_new: bool = False) -> redshift_connector.Connection:
    """
    Get or create a database connection.

    By default, returns the existing connection if one exists.
    Use force_new=True to create a fresh connection.

    Args:
        force_new: If True, closes existing connection and creates a new one

    Returns:
        redshift_connector.Connection: Active database connection

    Raises:
        RuntimeError: If connection cannot be established
    """
    global _connection

    # If forcing new connection, close existing one first
    if force_new and _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None

    # Return existing connection if available
    if _connection is not None:
        return _connection

    # Create new connection
    try:
        _connection = redshift_connector.connect(
            host=HOST,
            database=DBNAME,
            port=PORT,
            user=USER,
            password=_read_password()
        )
        return _connection
    except Exception as e:
        raise RuntimeError(f"Failed to create database connection: {e}")


def close_connection() -> None:
    """Close the active database connection if one exists."""
    global _connection

    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        finally:
            _connection = None


# ============================================================================
# DATA OPERATIONS
# ============================================================================

def pull_data(query: str, as_polars: bool = True) -> Union[pl.DataFrame, pd.DataFrame]:
    """
    Execute a SQL query and return results as a DataFrame.

    Args:
        query: SQL query string to execute
        as_polars: If True, return Polars DataFrame; if False, return Pandas DataFrame

    Returns:
        pl.DataFrame or pd.DataFrame: Query results

    Raises:
        RuntimeError: If query execution fails

    Example:
        df = pull_data("SELECT * FROM schema.table WHERE date >= '2024-01-01'")
    """
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(query)

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()

        if as_polars:
            return pl.DataFrame(rows, schema=columns, orient="row")
        else:
            return pd.DataFrame(rows, columns=columns)
    except Exception as e:
        raise RuntimeError(f"Error executing query: {e}")


def execute_query(query: str, commit: bool = True) -> None:
    """
    Execute a SQL query without returning results (for INSERT, UPDATE, DELETE, etc.).

    Args:
        query: SQL query string to execute
        commit: If True, commit the transaction; if False, you must commit manually

    Raises:
        RuntimeError: If query execution fails

    Example:
        execute_query("DELETE FROM schema.table WHERE date < '2024-01-01'")
    """
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        if commit:
            conn.commit()
        cursor.close()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error executing query: {e}")


def _format_value(value) -> str:
    """Format a value for SQL insertion."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "NULL"
    elif isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    elif isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    elif hasattr(value, 'isoformat'):  # date/datetime
        return "'" + str(value) + "'"
    else:
        return str(value)


def push_data(
    data: Union[pl.DataFrame, pd.DataFrame],
    table_name: str,
    if_exists: Literal["append", "replace", "fail"] = "append",
    batch_size: int = 5000,
    verbose: bool = True
) -> bool:
    """
    Upload a DataFrame to a Redshift table.

    Args:
        data: Polars or Pandas DataFrame to upload
        table_name: Full table name (e.g., "schema.table_name")
        if_exists: What to do if table exists:
            - "append": Insert data into existing table
            - "replace": Drop table and recreate (use with caution!)
            - "fail": Raise error if table exists
        batch_size: Number of rows per INSERT batch (default: 5000)
        verbose: If True, print progress messages

    Returns:
        bool: True if successful

    Raises:
        ValueError: If table_name is invalid or if_exists option is invalid
        RuntimeError: If upload fails
    """
    if "." not in table_name:
        raise ValueError(
            f"table_name must include schema: 'schema.table_name', got '{table_name}'"
        )

    if if_exists not in ("append", "replace", "fail"):
        raise ValueError(f"if_exists must be 'append', 'replace', or 'fail', got '{if_exists}'")

    # Extract rows and columns efficiently (avoid iterrows)
    if isinstance(data, pl.DataFrame):
        columns = data.columns
        rows = data.rows()
    else:
        columns = list(data.columns)
        rows = [tuple(row) for row in data.to_numpy()]

    total_rows = len(rows)

    if total_rows == 0:
        if verbose:
            print("Warning: DataFrame is empty, nothing to upload")
        return True

    conn = get_connection()

    # Handle if_exists options
    if if_exists == "fail":
        schema, table = table_name.split(".", 1)
        check_query = f"""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = '{schema}' AND table_name = '{table}'
        """
        cursor = conn.cursor()
        cursor.execute(check_query)
        exists = cursor.fetchone()[0] > 0
        cursor.close()

        if exists:
            raise RuntimeError(f"Table {table_name} already exists and if_exists='fail'")

    elif if_exists == "replace":
        if verbose:
            print(f"Dropping table {table_name} if it exists...")
        try:
            execute_query(f"DROP TABLE IF EXISTS {table_name}", commit=True)
        except Exception as e:
            raise RuntimeError(f"Failed to drop table: {e}")

    column_list = ", ".join(columns)
    batches = (total_rows + batch_size - 1) // batch_size

    if verbose:
        print(f"Uploading {total_rows:,} rows to {table_name} in {batches} batch(es)...")

    try:
        cursor = conn.cursor()

        for batch_idx in range(batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_rows)
            batch = rows[start_idx:end_idx]

            # Build VALUES clause from batch
            values_list = []
            for row in batch:
                row_values = ", ".join(_format_value(v) for v in row)
                values_list.append(f"({row_values})")

            insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES {', '.join(values_list)}"
            cursor.execute(insert_sql)

            if verbose:
                print(f"  Batch {batch_idx + 1}/{batches}: rows {start_idx + 1:,}-{end_idx:,}")

        conn.commit()  # Single commit at end
        cursor.close()

        if verbose:
            print(f"Successfully uploaded {total_rows:,} rows to {table_name}")

        return True

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error uploading data: {e}")
