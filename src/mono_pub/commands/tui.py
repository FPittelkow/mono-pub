import typer

app = typer.Typer(
    invoke_without_command=True,
    help="Launch the optional Textual terminal interface.",
)


@app.callback(invoke_without_command=True)
def launch(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return

    try:
        from mono_pub.tui_interface import MonoPubTuiApp
    except ModuleNotFoundError as error:
        if error.name != "textual":
            raise

        typer.echo(
            "The TUI requires Textual. Install it with: "
            "uv sync --extra tui"
        )
        raise typer.Exit(1) from error

    MonoPubTuiApp().run()
