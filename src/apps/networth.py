import datetime
import typer
from typing_extensions import Annotated
from typing import List, Optional

from database import create_tables, get_db_connection
from apps.transactions import TransactionType # New import

networth_app = typer.Typer()


@networth_app.callback()
def callback():
    """
    Track your net worth based on savings and investments.
    """
    create_tables()


@networth_app.command("update-investment")
def update_investment(
    amount: Annotated[float, typer.Argument(help="Current investment amount.")],
    date: Annotated[
        str, typer.Option(help="Date of the snapshot (DD-MM-YYYY).")
    ] = datetime.date.today().strftime("%d-%m-%Y"),
):
    """
    Update your investment snapshot.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        parsed_date = datetime.datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        typer.secho("Invalid date format. Please use DD-MM-YYYY.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    cursor.execute(
        "INSERT OR REPLACE INTO investment_snapshots (snapshot_date, amount) VALUES (?, ?)",
        (parsed_date, amount),
    )
    conn.commit()
    conn.close()
    typer.secho(f"Investment snapshot updated to {amount:+.2f} on {date}.", fg=typer.colors.GREEN)


@networth_app.command("show")
def show_net_worth(): # Removed savings_accounts parameter
    """
    Display your current net worth based on specified savings categories and latest investment snapshot.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    typer.secho("\nCalculating Net Worth...", bold=True)

    # 1. Get total savings from transactions with 'Savings' type and 'Cash' category
    # Sum of amounts for transactions where type is 'Savings' and category is 'Cash'
    cursor.execute(
        "SELECT SUM(amount) FROM transactions WHERE type = ? AND category = ?",
        (TransactionType.SAVINGS.value, "Cash")
    )
    total_savings = cursor.fetchone()[0] or 0.0
    typer.secho(f"\nTotal Savings (type 'Savings', category 'Cash'): {total_savings:>+10.2f}", bold=True, fg=typer.colors.BLUE)
    
    # 2. Get latest investment snapshot
    cursor.execute("SELECT amount, snapshot_date FROM investment_snapshots ORDER BY snapshot_date DESC LIMIT 1")
    latest_investment = cursor.fetchone()

    investment_amount = 0.0
    investment_date = "N/A"
    if latest_investment:
        investment_amount = latest_investment['amount']
        # Format date from YYYY-MM-DD to DD-MM-YYYY for display
        investment_date = datetime.datetime.strptime(latest_investment['snapshot_date'], "%Y-%m-%d").strftime("%d-%m-%Y")
        typer.secho(f"\nLatest Investment Snapshot ({investment_date}): {investment_amount:>+10.2f}", bold=True, fg=typer.colors.MAGENTA)
    else:
        typer.secho("\nNo investment snapshots found. Use 'networth update-investment' to add one.", fg=typer.colors.YELLOW)
    
    # 3. Calculate Net Worth
    net_worth = total_savings + investment_amount

    conn.close()

    typer.secho("\n----------------------------------", bold=True)
    typer.secho(f"Total Net Worth: {net_worth:>+10.2f}", bold=True, fg=typer.colors.GREEN if net_worth >= 0 else typer.colors.RED)
    typer.secho("----------------------------------", bold=True)