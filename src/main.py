import typer

from apps.budget import budget_app
from apps.transactions import transactions_app
from apps.reports import reports_app
from apps.targets import targets_app
from apps.networth import networth_app # New import

app = typer.Typer()

app.add_typer(budget_app, name="budget")
app.add_typer(transactions_app, name="transactions")
app.add_typer(reports_app, name="reports")
app.add_typer(targets_app, name="targets")
app.add_typer(networth_app, name="networth") # New subcommand


def main():
    app()


if __name__ == "__main__":
    main()
