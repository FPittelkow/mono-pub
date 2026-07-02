import typer

from mono_tools.commands.new import app as new_app
from mono_tools.commands.release import app as release_app

app = typer.Typer()

app.add_typer(new_app, name="new")
app.add_typer(release_app, name="release")

if __name__ == "__main__":
    app()
