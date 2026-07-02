import typer

app = typer.Typer()


@app.command()
def publish():
    typer.echo("open")

