import typer

app = typer.Typer()


@app.command()
def open():
    typer.echo("open")

