import typer

from mono_tools.commands.new import app as new_app
from mono_tools.commands.release import app as release_app
from mono_tools.commands.publish import app as publish_app
from mono_tools.commands.list import app as list_app
from mono_tools.commands.open import app as open_app

app = typer.Typer()

app.add_typer(new_app, name="new")
app.add_typer(release_app, name="release")
app.add_typer(list_app, name="list")
app.add_typer(open_app, name="open")
app.add_typer(publish_app, name="publish")

if __name__ == "__main__":
    app()
