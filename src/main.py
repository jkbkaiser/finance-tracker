import typer

from apps.budget import budget_app
from apps.transactions import transactions_app
from apps.reports import reports_app  # New import

app = typer.Typer()

app.add_typer(budget_app, name="budget")
app.add_typer(transactions_app, name="transactions")
app.add_typer(reports_app, name="reports")  # New subcommand


def main():
    app()


if __name__ == "__main__":
    main()
