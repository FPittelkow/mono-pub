from datetime import date
from pathlib import Path
import subprocess

from jinja2 import Environment, FileSystemLoader
from rich.markup import escape
from rich.text import Text
from slugify import slugify
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Select

from mono_pub.commands.open import build_editor_command
from mono_pub.config import load_config
from mono_pub.process.assets import MissingImageError
from mono_pub.process.publish import (
    DirtyPublishRepositoryError,
    GitCommandError,
    GitRepositoryError,
    JekyllCommandError,
    PublishResult,
    publish_type,
)
from mono_pub.process.release import ExistingReleaseError, MissingRequiredFieldsError, release_type
from mono_pub.process.release_config import PATH_KEYS_BY_TYPE

CONTENT_TYPES = (
    ("Post", "post"),
    ("Project", "project"),
    ("Music", "music"),
)


class MonoPubTuiApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #workspace {
        height: 1fr;
        padding: 1;
    }

    #sidebar {
        width: 34;
        padding-right: 1;
    }

    #main {
        width: 1fr;
    }

    .panel {
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }

    .section-title {
        text-style: bold;
        margin-bottom: 1;
    }

    Button {
        width: 100%;
        margin-top: 1;
    }

    #status {
        height: 1fr;
    }

    #overview {
        height: 2fr;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    TITLE = "mono-pub"
    SUB_TITLE = "Textual publishing interface"

    def __init__(self):
        super().__init__()
        self.config: dict | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="workspace"):
            with Vertical(id="sidebar"):
                with Vertical(classes="panel"):
                    yield Label("Content", classes="section-title")
                    yield Select(CONTENT_TYPES, value="post", id="content-type")
                    yield Input(placeholder="Draft title", id="draft-title")
                    yield Button("Create draft", id="create-draft", variant="primary")
                with Vertical(classes="panel"):
                    yield Label("Actions", classes="section-title")
                    yield Button("Open drafts", id="open")
                    yield Button("Release marked drafts", id="release")
                    yield Button("Publish files only", id="publish-no-git")
                    yield Button("Publish and push", id="publish")
                    yield Button("Dry run preview", id="dry-run")
                    yield Button("Refresh", id="refresh")
            with Vertical(id="main"):
                yield RichLog(id="overview", classes="panel", wrap=True, highlight=True)
                yield RichLog(id="status", wrap=True, highlight=True)
        yield Footer()

    def on_mount(self):
        self.theme = "gruvbox"
        self.load_configuration()
        self.refresh_summary()

    def action_refresh(self):
        self.load_configuration()
        self.refresh_summary()

    def on_button_pressed(self, event: Button.Pressed):
        actions = {
            "create-draft": self.create_draft,
            "open": self.open_selected,
            "release": self.release_selected,
            "publish-no-git": lambda: self.publish_selected(no_git=True),
            "publish": lambda: self.publish_selected(),
            "dry-run": lambda: self.publish_selected(no_git=True, dry_run=True),
            "refresh": self.action_refresh,
        }

        action = actions.get(event.button.id or "")
        if action is not None:
            action()

    def load_configuration(self):
        try:
            self.config = load_config()
        except Exception as error:
            self.config = None
            self.log_message(f"[red]Configuration error:[/red] {error}")

    def refresh_summary(self):
        overview = self.query_one("#overview", RichLog)
        overview.clear()

        if self.config is None:
            self.write_log(overview, "Configuration could not be loaded.")
            return

        self.write_log(overview, "[b]Library overview[/b]")
        for content_type in PATH_KEYS_BY_TYPE:
            path_key = PATH_KEYS_BY_TYPE[content_type]
            self.write_file_group(overview, content_type, "Drafts", "drafts_path", path_key)
            self.write_file_group(overview, content_type, "Releases", "releases_path", path_key)

    def write_file_group(
        self,
        overview: RichLog,
        content_type: str,
        label: str,
        group_key: str,
        path_key: str,
    ):
        files = self.markdown_files(group_key, path_key)
        self.write_log(
            overview,
            f"\n[b]{escape(content_type.title())} {escape(label)} ({len(files)})[/b]",
        )

        if not files:
            self.write_log(overview, "  [dim]No files[/dim]")
            return

        for file in files:
            self.write_log(overview, f"  {escape(file.name)}")

    def create_draft(self):
        if self.config is None:
            self.log_message("[red]Cannot create a draft until configuration loads.[/red]")
            return

        content_type = self.selected_content_type()
        title = self.query_one("#draft-title", Input).value.strip()

        if not title:
            self.log_message("[yellow]Enter a title before creating a draft.[/yellow]")
            return

        try:
            target = create_draft(self.config, content_type, title)
        except FileExistsError as error:
            path = error.filename or error.args[0]
            self.log_message(f"[red]Draft already exists:[/red] {path}")
            return
        except Exception as error:
            self.log_message(f"[red]Could not create draft:[/red] {error}")
            return

        self.query_one("#draft-title", Input).value = ""
        self.log_message(f"[green]Created draft:[/green] {target}")
        self.refresh_summary()

    def open_selected(self):
        if self.config is None:
            self.log_message("[red]Cannot open drafts until configuration loads.[/red]")
            return

        content_type = self.selected_content_type()
        path_key = PATH_KEYS_BY_TYPE[content_type]
        editor_command = self.config.get("editor_command")

        if not editor_command:
            self.log_message("[red]Missing editor_command in configuration.[/red]")
            return

        draft_path = Path(self.config["drafts_path"][path_key])

        if not draft_path.exists():
            self.log_message(f"[red]Draft path does not exist:[/red] {draft_path}")
            return

        try:
            command = build_editor_command(editor_command, draft_path)
            subprocess.Popen(command)
        except FileNotFoundError:
            self.log_message(f"[red]Editor command not found:[/red] {command[0]}")
            return
        except ValueError as error:
            self.log_message(f"[red]Could not open drafts:[/red] {error}")
            return

        self.log_message(f"[green]Opened drafts:[/green] {draft_path}")

    def release_selected(self):
        if self.config is None:
            self.log_message("[red]Cannot release until configuration loads.[/red]")
            return

        content_type = self.selected_content_type()

        try:
            released = release_type(self.config, content_type)
        except MissingRequiredFieldsError as error:
            self.log_message(f"[red]Missing {error.fields}:[/red] {error.path}")
            return
        except ExistingReleaseError as error:
            self.log_message(f"[red]Release already exists:[/red] {error.path}")
            return
        except MissingImageError as error:
            self.log_message(f"[red]Image not found:[/red] {error.path}")
            return
        except Exception as error:
            self.log_message(f"[red]Release failed:[/red] {error}")
            return

        if not released:
            self.log_message(f"No marked {content_type} drafts to release.")
        else:
            self.log_message(f"[green]Released {len(released)} {content_type} draft(s).[/green]")
            for path in released:
                self.log_message(f"  {path}")

        self.refresh_summary()

    def publish_selected(self, *, no_git: bool = False, dry_run: bool = False):
        if self.config is None:
            self.log_message("[red]Cannot publish until configuration loads.[/red]")
            return

        content_type = self.selected_content_type()

        try:
            result = publish_type(
                self.config,
                content_type,
                copy_files=True,
                run_git=not no_git and not dry_run,
                dry_run=dry_run,
            )
        except DirtyPublishRepositoryError as error:
            self.log_message(f"[red]Publish repository is dirty:[/red] {error.base_dir}")
            self.log_message(error.status)
            return
        except (GitCommandError, GitRepositoryError, JekyllCommandError) as error:
            self.log_message(f"[red]{error}[/red]")
            if error.output:
                self.log_message(error.output)
            return
        except Exception as error:
            self.log_message(f"[red]Publish failed:[/red] {error}")
            return

        self.report_publish_result(result)
        self.refresh_summary()

    def report_publish_result(self, result: PublishResult):
        self.log_message(
            f"[green]Published {len(result.files)} {result.content_type} files "
            f"and {len(result.asset_dirs)} asset directories.[/green]"
        )

        for path in result.files:
            self.log_message(f"  {path}")

        for path in result.asset_dirs:
            self.log_message(f"  {path}")

        if result.git is not None:
            self.log_message(result.git.message)

        if result.jekyll is not None:
            self.log_message(
                f"Jekyll server started in {result.jekyll.base_dir} "
                f"on http://127.0.0.1:{result.jekyll.port}"
            )

    def markdown_files(self, group_key: str, path_key: str) -> list[Path]:
        path = Path(self.config[group_key][path_key])
        return sorted(path.glob("*.md")) if path.exists() else []

    def selected_content_type(self) -> str:
        value = self.query_one("#content-type", Select).value
        return str(value)

    def log_message(self, message: str):
        self.write_log(self.query_one("#status", RichLog), message)

    def write_log(self, log: RichLog, message: str):
        log.write(Text.from_markup(message))


def create_draft(config: dict, content_type: str, title: str) -> Path:
    today = date.today()
    slug = slugify(title)
    path_key = PATH_KEYS_BY_TYPE[content_type]
    target_dir = Path(config["drafts_path"][path_key])
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{today.isoformat()}-{slug}.md"

    if target.exists():
        raise FileExistsError(target)

    env = Environment(loader=FileSystemLoader(config["templates_path"]))
    template = env.get_template(f"{content_type}.md.j2")
    context = {
        "title": title,
        "date": today.isoformat(),
        "author": config["author"],
        "type": content_type,
    }

    if content_type == "music":
        context["permalink"] = slug

    target.write_text(template.render(**context), encoding="utf-8")
    return target
