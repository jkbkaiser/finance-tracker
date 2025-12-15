import datetime
import typer
from typing_extensions import Annotated
from typing import Optional

from database import create_tables, get_db_connection


targets_app = typer.Typer()


@targets_app.callback()
def callback():
    """
    Manage your financial targets.
    """
    create_tables()


@targets_app.command("add")
def add_target(
    item_name: Annotated[str, typer.Argument(help="Name of the target item.")],
    price: Annotated[float, typer.Argument(help="Estimated price of the target.")],
    priority: Annotated[
        int,
        typer.Option(help="Priority of the target (1-5, 1 being highest)."),
    ] = 1,
):
    """
    Add a new financial target.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO targets_items (item_name, price, priority, purchased) VALUES (?, ?, ?, ?)",
        (item_name, price, priority, 0),
    )
    conn.commit()
    conn.close()
    typer.secho(f"Added '{item_name}' to targets with price {price:.2f} and priority {priority}.", fg=typer.colors.GREEN)


@targets_app.command("list")
def list_targets(
    all: Annotated[
        bool,
        typer.Option("--all", "-a", help="List all targets, including achieved ones."),
    ] = False,
):
    """
    List financial targets.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, item_name, price, priority, purchased FROM targets_items"
    params = []
    
    if not all:
        query += " WHERE purchased = ?"
        params.append(0)
    
    query += " ORDER BY priority ASC, id ASC"
    
    cursor.execute(query, tuple(params))
    items = cursor.fetchall()
    conn.close()

    if not items:
        typer.secho("No financial targets found.", fg=typer.colors.YELLOW)
        return

    typer.secho("\nFinancial Targets:", bold=True)
    print("--------------------------------------------------------------------")
    
    max_name_len = max(len(item['item_name']) for item in items)
    if max_name_len < len("Target Name"):
        max_name_len = len("Target Name")
    
    # Header
    typer.secho(
        f"{'ID':<4} {'Target Name':<{max_name_len}} {'Price':>10} {'Priority':>8} {'Achieved':>9}",
        bold=True,
    )
    print("-" * (4 + 1 + max_name_len + 1 + 10 + 1 + 8 + 1 + 9))

    for item in items:
        achieved_status = "Yes" if item['purchased'] else "No"
        color = typer.colors.GREEN if item['purchased'] else typer.colors.CYAN
        
        typer.secho(
            f"{item['id']:<4} {item['item_name']:<{max_name_len}} {item['price']:>10.2f} {item['priority']:>8} {achieved_status:>9}",
            fg=color,
        )
    print("-" * (4 + 1 + max_name_len + 1 + 10 + 1 + 8 + 1 + 9))


@targets_app.command("achieve")
def achieve_target(
    item_id: Annotated[int, typer.Argument(help="ID of the target to mark as achieved.")],
):
    """
    Mark a financial target as achieved.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE targets_items SET purchased = ? WHERE id = ?",
        (1, item_id),
    )
    conn.commit()
    conn.close()
    if cursor.rowcount:
        typer.secho(f"Target with ID {item_id} marked as achieved.", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Target with ID {item_id} not found.", fg=typer.colors.RED)


@targets_app.command("delete")
def delete_target(
    item_id: Annotated[int, typer.Argument(help="ID of the target to delete.")],
):
    """
    Delete a financial target.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM targets_items WHERE id = ?",
        (item_id,),
    )
    conn.commit()
    conn.close()
    if cursor.rowcount:
        typer.secho(f"Target with ID {item_id} deleted.", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Target with ID {item_id} not found.", fg=typer.colors.RED)
