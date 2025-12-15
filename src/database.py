import sqlite3
import typer

DB_FILE = "finances.db"


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """Create the necessary tables in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Drop the old budget table if it exists
    cursor.execute("DROP TABLE IF EXISTS budget")

    # Create the budget_items table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            amount REAL NOT NULL,
            UNIQUE(type, category, month, year)
        )
    """
    )

    # Create the transactions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            category TEXT,
            account TEXT NOT NULL
        )
    """
    )
    
    # Create the targets_items table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS targets_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            price REAL NOT NULL,
            priority INTEGER DEFAULT 1,
            purchased INTEGER DEFAULT 0
        )
    """
    )
    
    # Create the investment_snapshots table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS investment_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


def close_connection(conn: sqlite3.Connection, exception: typer.Exit):
    if conn:
        conn.close()


def get_distinct_categories(incomplete: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT category FROM budget_items WHERE category LIKE ?",
        (f"%{incomplete}%",),
    )
    categories = [row["category"] for row in cursor.fetchall()]
    conn.close()
    return categories


def get_distinct_accounts(incomplete: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT account FROM transactions WHERE account LIKE ?",
        (f"%{incomplete}%",),
    )
    accounts = [row["account"] for row in cursor.fetchall()]
    conn.close()
    return accounts
