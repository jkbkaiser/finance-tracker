import typer

from apps.budget import budget_app
from apps.transactions import transactions_app

app = typer.Typer()

app.add_typer(budget_app, name="budget")
app.add_typer(transactions_app, name="transactions")


def main():
    app()


if __name__ == "__main__":
    main()
