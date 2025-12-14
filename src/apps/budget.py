import datetime
from enum import Enum

import typer
from typing_extensions import Annotated

from database import create_tables, get_db_connection, get_distinct_categories


class BudgetType(str, Enum):
    INCOME = "Income"
    EXPENSE = "Expense"
    SAVINGS = "Savings"


budget_app = typer.Typer()


def complete_category(incomplete: str):
    for c in get_distinct_categories(incomplete):
        yield c


@budget_app.callback()
def callback():
    """
    Manage the budget.
    """
    create_tables()


@budget_app.command()
def update(
    type: Annotated[BudgetType, typer.Argument(help="The budget item type.")],
    category: Annotated[
        str,
        typer.Argument(help="The budget category.", autocompletion=complete_category),
    ],
    amount: Annotated[float, typer.Argument(help="The budget amount.")],
    month: Annotated[
        int, typer.Option(help="The month for the budget item (1-12).")
    ] = datetime.date.today().month,
    year: Annotated[
        int, typer.Option(help="The year for the budget item.")
    ] = datetime.date.today().year,
):
    """
    Update or add a budget item.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO budget_items (type, category, month, year, amount) VALUES (?, ?, ?, ?, ?)",
        (type.value, category, month, year, amount),
    )
    conn.commit()
    conn.close()
    print(
        f"Budget item '{type.value} - {category}' for {month}/{year} set to {amount:.2f}"
    )


@budget_app.command()
def summarize(
    month: Annotated[
        int, typer.Option(help="The month to summarize (1-12).")
    ] = datetime.date.today().month,
    year: Annotated[
        int, typer.Option(help="The year to summarize.")
    ] = datetime.date.today().year,
):
    """
    Summarize the budget for a given month and year.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT type, category, amount FROM budget_items WHERE month = ? AND year = ? ORDER BY type, amount DESC",
        (month, year),
    )
    budget_items = cursor.fetchall()
    conn.close()

    if not budget_items:
        typer.secho(
            f"No budget items found for {month}/{year}.", fg=typer.colors.YELLOW
        )
        return

    typer.secho(f"Budget Summary for {month}/{year}:", bold=True)
    print("--------------------")

    grouped_items = {bt.value: [] for bt in BudgetType}
    for item in budget_items:
        if item["type"] in grouped_items:
            grouped_items[item["type"]].append(item)

    max_category_len = 0
    # Also consider the "Total X:" string for alignment
    for item in budget_items:
        if len(item["category"]) > max_category_len:
            max_category_len = len(item["category"])
    # Ensure totals also align with longest category
    max_category_len = max(
        max_category_len,
        len("Total Income:"),
        len("Total Expense:"),
        len("Total Savings:"),
    )

    total_by_type = {
        BudgetType.INCOME.value: 0.0,
        BudgetType.EXPENSE.value: 0.0,
        BudgetType.SAVINGS.value: 0.0,
    }

    type_colors = {
        BudgetType.INCOME.value: typer.colors.GREEN,
        BudgetType.EXPENSE.value: typer.colors.RED,
        BudgetType.SAVINGS.value: typer.colors.YELLOW,
    }

    for budget_type in BudgetType:
        type_name = budget_type.value
        items_in_type = grouped_items[type_name]
        type_color = type_colors[type_name]

        if items_in_type:
            typer.secho(f"\n{type_name}:", fg=type_color, bold=True)
            type_total = 0.0
            for item in items_in_type:
                typer.secho(
                    f"  {item['category']:<{max_category_len}}   {item['amount']:.2f}",
                    fg=type_color,
                )
                type_total += item["amount"]
            typer.secho(
                f"  {'Total ' + type_name + ':':<{max_category_len}}   {type_total:.2f}",
                fg=type_color,
                bold=True,
            )
            total_by_type[type_name] = type_total
        else:
            typer.secho(f"\n{type_name}: No items", fg=type_color)

    print("\n--------------------")
    typer.secho("Summary of Totals:", bold=True)
    max_total_len = max(len("Total Income:"), len("Total Cost:"), len("Total Savings:"))
    typer.secho(
        f"  {'Total Income:':<{max_total_len}}   {total_by_type[BudgetType.INCOME.value]:.2f}",
        fg=typer.colors.GREEN,
    )
    typer.secho(
        f"  {'Total Expense:':<{max_total_len}}   {total_by_type[BudgetType.EXPENSE.value]:.2f}",
        fg=typer.colors.RED,
    )
    typer.secho(
        f"  {'Total Savings:':<{max_total_len}}   {total_by_type[BudgetType.SAVINGS.value]:.2f}",
        fg=typer.colors.YELLOW,
    )

    print("--------------------")
    surplus = (
        total_by_type[BudgetType.INCOME.value]
        - total_by_type[BudgetType.EXPENSE.value]
        - total_by_type[BudgetType.SAVINGS.value]
    )
    result_text = "Surplus" if surplus >= 0 else "Deficit"
    surplus_color = typer.colors.GREEN if surplus >= 0 else typer.colors.RED
    typer.secho(f"Total {result_text}: {surplus:.2f}", fg=surplus_color, bold=True)


@budget_app.command()
def delete(
    type: Annotated[BudgetType, typer.Argument(help="The budget item type to delete.")],
    category: Annotated[
        str,
        typer.Argument(
            help="The budget category to delete.", autocompletion=complete_category
        ),
    ],
    month: Annotated[
        int, typer.Option(help="The month for the budget item (1-12).")
    ] = datetime.date.today().month,
    year: Annotated[
        int, typer.Option(help="The year for the budget item.")
    ] = datetime.date.today().year,
):
    """
    Delete a specific budget item for a given month/year.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "DELETE FROM budget_items WHERE type = ? AND category = ? AND month = ? AND year = ?"
    params = [type.value, category, month, year]

    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()

    print(f"Deleted '{type.value} - {category}' for {month}/{year}.")
