import datetime
from enum import Enum
from typing import Optional

import typer
from typing_extensions import Annotated

from database import (create_tables, get_db_connection, get_distinct_accounts,
                      get_distinct_categories)


class TransactionType(str, Enum):
    INCOME = "Income"
    EXPENSE = "Expense"


transactions_app = typer.Typer()


def complete_category(incomplete: str):
    for c in get_distinct_categories(incomplete):
        yield c


def complete_account(incomplete: str):
    for a in get_distinct_accounts(incomplete):
        yield a


@transactions_app.callback()
def callback():
    """
    Manage transactions.
    """
    create_tables()


@transactions_app.command("add")
def add_transaction(
    amount: Annotated[float, typer.Argument(help="Amount of the transaction.")],
    type: Annotated[
        TransactionType, typer.Argument(help="Type of the transaction.")
    ],
    category: Annotated[
        str,
        typer.Argument(help="Budget category for the transaction.", autocompletion=complete_category),
    ],
    account: Annotated[
        str,
        typer.Argument(help="Account for the transaction.", autocompletion=complete_account),
    ],
    date: Annotated[
        str, typer.Argument(help="Date of the transaction (YYYY-MM-DD).")
    ],
    description: Annotated[Optional[str], typer.Argument(help="Description of the transaction.")] = None,
):
    """
    Add a new transaction.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transactions (date, description, amount, type, category, account) VALUES (?, ?, ?, ?, ?, ?)",
        (date, description, amount, type.value, category, account),
    )
    conn.commit()
    conn.close()
    typer.secho(
        f"Added transaction: {description} ({amount:.2f}) on {date}",
        fg=typer.colors.GREEN,
    )


@transactions_app.command("delete")
def delete_transaction(
    transaction_id: Annotated[int, typer.Argument(help="ID of the transaction to delete.")],
):
    """
    Delete a transaction by its ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    typer.secho(f"Deleted transaction with ID: {transaction_id}", fg=typer.colors.GREEN)


@transactions_app.command("summarize")
def summarize_transactions(
    month: Annotated[
        Optional[int], typer.Option(help="The month to summarize (1-12).")
    ] = None,
    year: Annotated[
        Optional[int], typer.Option(help="The year to summarize.")
    ] = None,
    type: Annotated[
        Optional[TransactionType], typer.Option(help="Filter by transaction type.")
    ] = None,
    category: Annotated[
        Optional[str],
        typer.Option(help="Filter by budget category.", autocompletion=complete_category),
    ] = None,
    account: Annotated[
        Optional[str],
        typer.Option(help="Filter by account.", autocompletion=complete_account),
    ] = None,
):
    """
    Summarize transactions, with optional filters. Defaults to current month.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query_parts = ["SELECT id, date, description, amount, type, category, account FROM transactions WHERE 1=1"]
    params = []

    today = datetime.date.today()
    if month is None:
        month = today.month
    if year is None:
        year = today.year
    
    query_parts.append(" AND CAST(SUBSTR(date, 6, 2) AS INTEGER) = ?")
    params.append(month)
    query_parts.append(" AND CAST(SUBSTR(date, 1, 4) AS INTEGER) = ?")
    params.append(year)

    if type:
        query_parts.append(" AND type = ?")
        params.append(type.value)
    if category:
        query_parts.append(" AND category = ?")
        params.append(category)
    if account:
        query_parts.append(" AND account = ?")
        params.append(account)

    query_parts.append(" ORDER BY date DESC, id DESC")

    query = " ".join(query_parts)
    cursor.execute(query, tuple(params))
    transactions = cursor.fetchall()
    conn.close()

    if not transactions:
        typer.secho(f"No transactions found for the given criteria.", fg=typer.colors.YELLOW)
        return

    typer.secho(f"Transactions Summary:", bold=True)
    print("--------------------------------------------------------------------")

    # Determine max widths for formatting
    max_id_len = max(len(str(t['id'])) for t in transactions)
    if max_id_len < len("ID"):
        max_id_len = len("ID")
    max_desc_len = max(len(t['description']) for t in transactions)
    max_cat_len = max(len(t['category']) if t['category'] else len("N/A") for t in transactions)
    max_acc_len = max(len(t['account']) for t in transactions)
    
    # Adjust description length for small values to ensure minimal width
    if max_desc_len < len("Description"):
        max_desc_len = len("Description")
    if max_cat_len < len("Category"):
        max_cat_len = len("Category")
    if max_acc_len < len("Account"):
        max_acc_len = len("Account")


    # Header
    typer.secho(f"{'ID':<{max_id_len}} {'Date':<10} {'Amount':>10} {'Type':<8} {'Category':<{max_cat_len}} {'Account':<{max_acc_len}} {'Description':<{max_desc_len}}", bold=True)
    # Separator line length
    separator_len = max_id_len + 1 + 10 + 1 + 10 + 1 + 8 + 1 + max_cat_len + 1 + max_acc_len + 1 + max_desc_len
    print("-" * separator_len) 

    total_amount = 0.0
    for t in transactions:
        color = typer.colors.GREEN if t['type'] == TransactionType.INCOME.value else typer.colors.RED
        cat = t['category'] if t['category'] else "N/A"
        typer.secho(
            f"{t['id']:<{max_id_len}} {t['date']:<10} {t['amount']:>10.2f} {t['type']:<8} {cat:<{max_cat_len}} {t['account']:<{max_acc_len}} {t['description']:<{max_desc_len}}",
            fg=color
        )
        total_amount += t['amount']
    
    print("-" * separator_len)
    typer.secho(f"Total Amount: {total_amount:.2f}", bold=True)
