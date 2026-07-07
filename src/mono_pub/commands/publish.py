import typer

from mono_pub.config import load_config
from mono_pub.process.publish import (
    DirtyPublishRepositoryError,
    GitCommandError,
    GitRepositoryError,
    JekyllCommandError,
    PublishResult,
    publish_type,
)

app = typer.Typer(
    help="Publish to Jekyll.",
    no_args_is_help=True,
)


@app.command()
def post(
    no_git: bool = typer.Option(False, "--no-git", help="Skip git add/commit/push."),
    git_only: bool = typer.Option(False, "--git", help="Only run git add/commit/push."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Launch local Jekyll preview."),
):
    publish_content_type("post", no_git=no_git, git_only=git_only, dry_run=dry_run)


@app.command()
def project(
    no_git: bool = typer.Option(False, "--no-git", help="Skip git add/commit/push."),
    git_only: bool = typer.Option(False, "--git", help="Only run git add/commit/push."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Launch local Jekyll preview."),
):
    publish_content_type("project", no_git=no_git, git_only=git_only, dry_run=dry_run)


@app.command()
def music(
    no_git: bool = typer.Option(False, "--no-git", help="Skip git add/commit/push."),
    git_only: bool = typer.Option(False, "--git", help="Only run git add/commit/push."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Launch local Jekyll preview."),
):
    publish_content_type("music", no_git=no_git, git_only=git_only, dry_run=dry_run)


@app.command("all")
def all_types(
    no_git: bool = typer.Option(False, "--no-git", help="Skip git add/commit/push."),
    git_only: bool = typer.Option(False, "--git", help="Only run git add/commit/push."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Launch local Jekyll preview."),
):
    validate_publish_options(no_git, git_only, dry_run)
    config = load_config()
    for content_type in ("post", "project", "music"):
        report_result(run_publish(config, content_type, no_git, git_only, dry_run))


def publish_content_type(
    content_type: str,
    *,
    no_git: bool,
    git_only: bool,
    dry_run: bool,
):
    validate_publish_options(no_git, git_only, dry_run)
    config = load_config()
    report_result(run_publish(config, content_type, no_git, git_only, dry_run))


def run_publish(
    config: dict,
    content_type: str,
    no_git: bool,
    git_only: bool,
    dry_run: bool,
) -> PublishResult:
    try:
        return publish_type(
            config,
            content_type,
            copy_files=not git_only,
            run_git=not no_git and not dry_run,
            dry_run=dry_run,
        )
    except DirtyPublishRepositoryError as error:
        typer.echo(f"Publish repository is dirty: {error.base_dir}")
        typer.echo(error.status)
        raise typer.Exit(1)
    except GitCommandError as error:
        typer.echo(str(error))
        if error.output:
            typer.echo(error.output)
        raise typer.Exit(1)
    except GitRepositoryError as error:
        typer.echo(str(error))
        if error.output:
            typer.echo(error.output)
        raise typer.Exit(1)
    except JekyllCommandError as error:
        typer.echo(str(error))
        if error.output:
            typer.echo(error.output)
        raise typer.Exit(1)


def validate_publish_options(no_git: bool, git_only: bool, dry_run: bool):
    if no_git and git_only:
        typer.echo("--no-git and --git cannot be used together.")
        raise typer.Exit(1)

    if dry_run and git_only:
        typer.echo("--dry-run and --git cannot be used together.")
        raise typer.Exit(1)


def report_result(result: PublishResult):
    typer.echo(
        f"Published {len(result.files)} {result.content_type} files "
        f"and {len(result.asset_dirs)} asset directories."
    )

    for path in result.files:
        typer.echo(f"  {path}")

    for path in result.asset_dirs:
        typer.echo(f"  {path}")

    if result.git is not None:
        typer.echo(result.git.message)

    if result.jekyll is not None:
        typer.echo(
            f"Jekyll server started in {result.jekyll.base_dir} "
            f"on http://127.0.0.1:{result.jekyll.port}"
        )
