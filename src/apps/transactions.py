import datetime
from enum import Enum
from typing import Optional

import typer
from typing_extensions import Annotated

from database import (
    create_tables,
    get_db_connection,
    get_distinct_accounts,
    get_distinct_categories,
)


class TransactionType(str, Enum):
    INCOME = "Income"
    EXPENSE = "Expense"
    TRANSFER = "Transfer"
    SAVINGS = "Savings" # New entry


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
    type: Annotated[TransactionType, typer.Argument(help="Type of the transaction.")],
    category: Annotated[
        str,
        typer.Argument(
            help="Budget category for the transaction.",
            autocompletion=complete_category,
        ),
    ],
    account: Annotated[
        str,
        typer.Argument(
            help="Account for the transaction.", autocompletion=complete_account
        ),
    ],
    date: Annotated[str, typer.Argument(help="Date of the transaction (DD-MM-YYYY).")],
    description: Annotated[
        Optional[str], typer.Argument(help="Description of the transaction.")
    ] = None,
):
    """
    Add a new transaction.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        parsed_date = datetime.datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        typer.secho("Invalid date format. Please use DD-MM-YYYY.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Adjust amount for expense type before inserting
    if type == TransactionType.EXPENSE:
        amount = -amount

    cursor.execute(
        "INSERT INTO transactions (date, description, amount, type, category, account) VALUES (?, ?, ?, ?, ?, ?)",
        (parsed_date, description, amount, type.value, category, account),
    )
    conn.commit()
    conn.close()
    typer.secho(
        f"Added transaction: {category} ({amount:+.2f}) on {date} '{description or ''}'",
        fg=typer.colors.GREEN,
    )


@transactions_app.command("delete")
def delete_transaction(
    transaction_id: Annotated[
        int, typer.Argument(help="ID of the transaction to delete.")
    ],
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
    year: Annotated[Optional[int], typer.Option(help="The year to summarize.")] = None,
    type: Annotated[
        Optional[TransactionType], typer.Option(help="Filter by transaction type.")
    ] = None,
    category: Annotated[
        Optional[str],
        typer.Option(
            help="Filter by budget category.", autocompletion=complete_category
        ),
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

    query_parts = [
        "SELECT id, date, description, amount, type, category, account FROM transactions WHERE 1=1"
    ]
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
        typer.secho(
            f"No transactions found for the given criteria.", fg=typer.colors.YELLOW
        )
        return

    typer.secho(f"Transactions Summary:", bold=True)
    print("--------------------------------------------------------------------")

    # Determine max widths for formatting
    COLUMN_PADDING = 3
    max_id_len = max(len(str(t["id"])) for t in transactions)
    if max_id_len < len("ID"):
        max_id_len = len("ID")
    max_desc_len = max(
        len(t["description"]) if t["description"] else 0 for t in transactions
    )
    if max_desc_len < len("Description"):
        max_desc_len = len("Description")
    max_cat_len = max(
        len(t["category"]) if t["category"] else len("N/A") for t in transactions
    )
    if max_cat_len < len("Category"):
        max_cat_len = len("Category")
    max_acc_len = max(len(t["account"]) for t in transactions)
    if max_acc_len < len("Account"):
        max_acc_len = len("Account")

    # Header
    typer.secho(
        f"{'ID':<{max_id_len + COLUMN_PADDING}} {'Date':<{10 + COLUMN_PADDING}} {'Amount':>{11 + COLUMN_PADDING}} {'Type':<{8 + COLUMN_PADDING}} {'Category':<{max_cat_len + COLUMN_PADDING}} {'Account':<{max_acc_len + COLUMN_PADDING}} {'Description':<{max_desc_len}}",
        bold=True,
    )
    # Separator line length
    separator_len = (
        max_id_len
        + COLUMN_PADDING
        + 10
        + COLUMN_PADDING
        + 11
        + COLUMN_PADDING
        + 8
        + COLUMN_PADDING
        + max_cat_len
        + COLUMN_PADDING
        + max_acc_len
        + COLUMN_PADDING
        + max_desc_len
    )
    print("-" * separator_len)

    total_amount = 0.0
    for t in transactions:
        color = typer.colors.GREEN
        display_amount_str = f"{t['amount']:+.2f}"  # Now all amounts are displayed with their stored sign

        if t["type"] == TransactionType.EXPENSE.value:
            color = typer.colors.RED
        elif t["type"] == TransactionType.TRANSFER.value:
            color = typer.colors.BLUE
        elif t["type"] == TransactionType.SAVINGS.value:
            color = typer.colors.CYAN

        cat = t["category"] if t["category"] else "N/A"
        desc = t["description"] if t["description"] else "N/A"
        typer.secho(
            f"{t['id']:<{max_id_len + COLUMN_PADDING}} {datetime.datetime.strptime(t['date'], '%Y-%m-%d').strftime('%d-%m-%Y'):<{10 + COLUMN_PADDING}} {display_amount_str:>{11 + COLUMN_PADDING}} {t['type']:<{8 + COLUMN_PADDING}} {cat:<{max_cat_len + COLUMN_PADDING}} {t['account']:<{max_acc_len + COLUMN_PADDING}} {desc:<{max_desc_len}}",
            fg=color,
        )
        total_amount += t[
            "amount"
        ]  # Sum all amounts directly, as they are stored with correct sign

    print("-" * separator_len)
    typer.secho(f"Total Amount: {total_amount:.2f}", bold=True)
