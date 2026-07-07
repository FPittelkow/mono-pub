import typer

from mono_pub.commands.new import app as new_app
from mono_pub.commands.release import app as release_app
from mono_pub.commands.publish import app as publish_app
from mono_pub.commands.list import app as list_app
from mono_pub.commands.open import app as open_app
from mono_pub.commands.tui import app as tui_app

app = typer.Typer(
    no_args_is_help=True
)

app.add_typer(new_app, name="new")
app.add_typer(open_app, name="open")
app.add_typer(list_app, name="list")
app.add_typer(release_app, name="release")
app.add_typer(publish_app, name="publish")
app.add_typer(tui_app, name="tui")

if __name__ == "__main__":
    app()
