from datetime import date
from pathlib import Path

import typer
from slugify import slugify
from jinja2 import Environment, FileSystemLoader

app = typer.Typer()

@app.command()
def post(title: str):
    today = date.today()
    slug = slugify(title)
    filename = f"{today.isoformat()}-{slug}.md"

    posts_dir = Path("_posts")
    posts_dir.mkdir(exist_ok=True)

    target = posts_dir / filename

    if target.exists():
        typer.echo(f"Exists already: {target}")
        raise typer.Exit(1)

    env = Environment(loader=FileSystemLoader("mono_tools/templates"))
    template = env.get_template("post.md.j2")

    content = template.render(
        title=title,
        date=today.isoformat(),
    )

    target.write_text(content, encoding="utf-8")
    typer.echo(f"Created: {target}")

@app.command()
def page(title: str):
    print(title)