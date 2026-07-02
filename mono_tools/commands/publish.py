import typer

from mono_tools.config import load_config
from mono_tools.process.publish import PublishResult, publish_type

app = typer.Typer()


@app.command()
def post():
    publish_content_type("post")


@app.command()
def project():
    publish_content_type("project")


@app.command()
def music():
    publish_content_type("music")


@app.command("all")
def all_types():
    config = load_config()
    for content_type in ("post", "project", "music"):
        report_result(publish_type(config, content_type))


def publish_content_type(content_type: str):
    config = load_config()
    report_result(publish_type(config, content_type))


def report_result(result: PublishResult):
    typer.echo(
        f"Published {len(result.files)} {result.content_type} files "
        f"and {len(result.asset_dirs)} asset directories."
    )

    for path in result.files:
        typer.echo(f"  {path}")

    for path in result.asset_dirs:
        typer.echo(f"  {path}")
