import datetime
from enum import Enum

import typer
from typing_extensions import Annotated

from database import get_db_connection
from apps.transactions import TransactionType
from apps.budget import (
    BudgetType,
)  # Assuming BudgetType is also needed, and will be imported


reports_app = typer.Typer()


@reports_app.command("month")
def compare_expenses(
    month: Annotated[
        int, typer.Option(help="The month to compare (1-12).")
    ] = datetime.date.today().month,
    year: Annotated[
        int, typer.Option(help="The year to compare.")
    ] = datetime.date.today().year,
):
    """
    Generate a monthly expense report comparing actual expenses to budgeted expenses.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Get Budgeted Expenses per category
    budgeted_expenses_query = """
        SELECT category, amount FROM budget_items
        WHERE type = ? AND month = ? AND year = ?
    """
    cursor.execute(budgeted_expenses_query, (BudgetType.EXPENSE.value, month, year))
    budgeted_per_category = {
        row["category"]: row["amount"] for row in cursor.fetchall()
    }

    # 2. Get Actual Expenses per category from transactions
    actual_expenses_query = """
        SELECT category, SUM(amount) FROM transactions
        WHERE type = ? AND CAST(SUBSTR(date, 6, 2) AS INTEGER) = ? AND CAST(SUBSTR(date, 1, 4) AS INTEGER) = ?
        GROUP BY category
    """
    cursor.execute(actual_expenses_query, (TransactionType.EXPENSE.value, month, year))
    # Convert sum of negative amounts to positive for actual expenses
    # Using abs() to ensure positive magnitude, regardless of old data
    actual_per_category = {
        row["category"]: abs(row["SUM(amount)"]) for row in cursor.fetchall()
    }

    conn.close()

    all_categories = sorted(
        list(set(budgeted_per_category.keys()) | set(actual_per_category.keys()))
    )

    all_categories = sorted(
        list(set(budgeted_per_category.keys()) | set(actual_per_category.keys()))
    )

    COLUMN_PADDING = 3

    # Determine max category length for formatting
    max_cat_len = max(len(category) for category in all_categories)
    if max_cat_len < len("Category"):
        max_cat_len = len("Category")
    if max_cat_len < len("Total:"):  # For the total row
        max_cat_len = len("Total:")

    typer.secho(f"\nExpense Comparison for {month}/{year}:", bold=True)

    # Calculate lengths for other columns
    budgeted_col_width = 10  # Default width for numbers like 100.00
    actual_col_width = 10
    diff_col_width = 10  # For +.2f or -.2f

    # Header
    header_str = (
        f"{'Category':<{max_cat_len + COLUMN_PADDING}}"
        f"{'Budgeted':>{budgeted_col_width + COLUMN_PADDING}}"
        f"{'Actual':>{actual_col_width + COLUMN_PADDING}}"
        f"{'Diff':>{diff_col_width}}"
    )
    typer.secho(header_str, bold=True)

    separator_len = (
        (max_cat_len + COLUMN_PADDING)
        + (budgeted_col_width + COLUMN_PADDING)
        + (actual_col_width + COLUMN_PADDING)
        + diff_col_width
    )
    print("-" * separator_len)

    total_budgeted = 0.0
    total_actual = 0.0

    for category in all_categories:
        budgeted = budgeted_per_category.get(category, 0.0)
        actual = actual_per_category.get(category, 0.0)
        difference = budgeted - actual

        total_budgeted += budgeted
        total_actual += actual

        diff_color = typer.colors.GREEN if difference >= 0 else typer.colors.RED
        formatted_difference = f"{difference:+.2f}"
        typer.secho(
            f"{category:<{max_cat_len + COLUMN_PADDING}}"
            f"{budgeted:>{budgeted_col_width + COLUMN_PADDING}.2f}"
            f"{actual:>{actual_col_width + COLUMN_PADDING}.2f}"
            f"{formatted_difference:>{diff_col_width}}",  # Apply padding to already formatted string
            fg=diff_color,
        )
    print("-" * separator_len)
    overall_difference = total_budgeted - total_actual
    overall_diff_color = (
        typer.colors.GREEN if overall_difference >= 0 else typer.colors.RED
    )

    formatted_overall_difference = f"{overall_difference:+.2f}"
    typer.secho(
        f"{'Total:':<{max_cat_len + COLUMN_PADDING}}"
        f"{total_budgeted:>{budgeted_col_width + COLUMN_PADDING}.2f}"
        f"{total_actual:>{actual_col_width + COLUMN_PADDING}.2f}"
        f"{formatted_overall_difference:>{diff_col_width}}",  # Apply padding to already formatted string
        fg=overall_diff_color,
        bold=True,
    )
    print("-" * separator_len)

    if overall_difference >= 0:
        typer.secho(
            f"Overall, you are under budget by {formatted_overall_difference}!",
            fg=typer.colors.GREEN,
            bold=True,
        )
    else:
        typer.secho(
            f"Overall, you are over budget by {formatted_overall_difference}!",
            fg=typer.colors.RED,
            bold=True,
        )


@reports_app.command("accumulated")
def accumulated_expenses(
    year: Annotated[
        int, typer.Option(help="The year to compare.")
    ] = datetime.date.today().year,
):
    """
    Generate an annual accumulated expense report comparing actual expenses to budgeted expenses per category.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Get Accumulated Budgeted Expenses per category for the year
    budgeted_expenses_query = """
        SELECT category, SUM(amount) FROM budget_items
        WHERE type = ? AND year = ?
        GROUP BY category
    """
    cursor.execute(budgeted_expenses_query, (BudgetType.EXPENSE.value, year))
    budgeted_per_category = {
        row["category"]: row["SUM(amount)"] for row in cursor.fetchall()
    }

    # 2. Get Accumulated Actual Expenses per category from transactions for the year
    actual_expenses_query = """
        SELECT category, SUM(amount) FROM transactions
        WHERE type = ? AND CAST(SUBSTR(date, 1, 4) AS INTEGER) = ?
        GROUP BY category
    """
    cursor.execute(actual_expenses_query, (TransactionType.EXPENSE.value, year))
    # Using abs() to ensure positive magnitude for actual expenses
    actual_per_category = {
        row["category"]: abs(row["SUM(amount)"]) for row in cursor.fetchall()
    }

    conn.close()

    all_categories = sorted(
        list(set(budgeted_per_category.keys()) | set(actual_per_category.keys()))
    )

    COLUMN_PADDING = 3

    # Determine max category length for formatting
    max_cat_len = max(len(category) for category in all_categories)
    if max_cat_len < len("Category"):
        max_cat_len = len("Category")
    if max_cat_len < len("Total:"):  # For the total row
        max_cat_len = len("Total:")

    typer.secho(f"\nAccumulated Expense Comparison for {year}:", bold=True)

    # Calculate lengths for other columns
    budgeted_col_width = 10
    actual_col_width = 10
    diff_col_width = 10

    # Header
    header_str = (
        f"{'Category':<{max_cat_len + COLUMN_PADDING}}"
        f"{'Budgeted':>{budgeted_col_width + COLUMN_PADDING}}"
        f"{'Actual':>{actual_col_width + COLUMN_PADDING}}"
        f"{'Diff':>{diff_col_width}}"
    )
    typer.secho(header_str, bold=True)

    separator_len = (
        (max_cat_len + COLUMN_PADDING)
        + (budgeted_col_width + COLUMN_PADDING)
        + (actual_col_width + COLUMN_PADDING)
        + diff_col_width
    )
    print("-" * separator_len)

    total_budgeted = 0.0
    total_actual = 0.0

    for category in all_categories:
        budgeted = budgeted_per_category.get(category, 0.0)
        actual = actual_per_category.get(category, 0.0)
        difference = budgeted - actual

        total_budgeted += budgeted
        total_actual += actual

        diff_color = typer.colors.GREEN if difference >= 0 else typer.colors.RED
        formatted_difference = f"{difference:+.2f}"
        typer.secho(
            f"{category:<{max_cat_len + COLUMN_PADDING}}"
            f"{budgeted:>{budgeted_col_width + COLUMN_PADDING}.2f}"
            f"{actual:>{actual_col_width + COLUMN_PADDING}.2f}"
            f"{formatted_difference:>{diff_col_width}}",
            fg=diff_color,
        )
    print("-" * separator_len)
    overall_difference = total_budgeted - total_actual
    overall_diff_color = (
        typer.colors.GREEN if overall_difference >= 0 else typer.colors.RED
    )

    formatted_overall_difference = f"{overall_difference:+.2f}"
    typer.secho(
        f"{'Total:':<{max_cat_len + COLUMN_PADDING}}"
        f"{total_budgeted:>{budgeted_col_width + COLUMN_PADDING}.2f}"
        f"{total_actual:>{actual_col_width + COLUMN_PADDING}.2f}"
        f"{formatted_overall_difference:>{diff_col_width}}",
        fg=overall_diff_color,
        bold=True,
    )
    print("-" * separator_len)

    if overall_difference >= 0:
        typer.secho(
            f"Overall, you are under budget by {formatted_overall_difference}!",
            fg=typer.colors.GREEN,
            bold=True,
        )
    else:
        typer.secho(
            f"Overall, you are over budget by {formatted_overall_difference}!",
            fg=typer.colors.RED,
            bold=True,
        )
