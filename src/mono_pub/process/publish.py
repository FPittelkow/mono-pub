from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess

import frontmatter

from mono_pub.process.release_config import path_key_for

ASSET_PATH_PATTERN = re.compile(r"assets/([^/\s\"')]+)")


@dataclass
class PublishResult:
    content_type: str
    files: list[Path]
    asset_dirs: list[Path]
    git: "GitResult | None" = None
    jekyll: "JekyllResult | None" = None


@dataclass
class GitResult:
    base_dir: Path
    committed: bool
    pushed: bool
    message: str


@dataclass
class JekyllResult:
    base_dir: Path
    port: int


class PublishError(Exception):
    pass


class DirtyPublishRepositoryError(PublishError):
    def __init__(self, base_dir: Path, status: str):
        self.base_dir = base_dir
        self.status = status
        super().__init__(f"Publish repository is dirty: {base_dir}")


class GitCommandError(PublishError):
    def __init__(self, command: list[str], cwd: Path, output: str):
        self.command = command
        self.cwd = cwd
        self.output = output
        super().__init__(f"Git command failed in {cwd}: {' '.join(command)}")


class GitRepositoryError(PublishError):
    def __init__(self, base_dir: Path, output: str):
        self.base_dir = base_dir
        self.output = output
        super().__init__(f"Publish base is not a git repository root: {base_dir}")


class JekyllCommandError(PublishError):
    def __init__(self, base_dir: Path, output: str):
        self.base_dir = base_dir
        self.output = output
        super().__init__(f"Could not start Jekyll in {base_dir}")


def publish_type(
    config: dict,
    content_type: str,
    *,
    copy_files: bool = True,
    run_git: bool = True,
    dry_run: bool = False,
) -> PublishResult:
    path_key = path_key_for(content_type)
    base_dir = Path(config["publish_base"][path_key])
    result = PublishResult(content_type, [], [])

    if copy_files and run_git:
        ensure_publish_git_repo(base_dir)
        ensure_clean_git_status(base_dir)

    if copy_files:
        result = publish_files(
            content_type,
            Path(config["releases_path"][path_key]),
            Path(config["assets_path"][path_key]),
            Path(config["publish_path"][path_key]),
            Path(config["publish_assets_path"][path_key]),
        )

    if run_git:
        result.git = run_git_publish(base_dir, content_type)

    if dry_run:
        result.jekyll = run_jekyll_server(
            base_dir,
            int(config.get("dry_run_port", {}).get(path_key, 4000)),
        )

    return result


def publish_files(
    content_type: str,
    releases_dir: Path,
    release_assets_dir: Path,
    publish_dir: Path,
    publish_assets_dir: Path,
) -> PublishResult:
    release_files = sorted(releases_dir.glob("*.md"))
    published_files = copy_release_files(release_files, publish_dir)
    published_assets = copy_referenced_assets(
        release_files,
        release_assets_dir,
        publish_assets_dir,
    )

    return PublishResult(content_type, published_files, published_assets)


def copy_release_files(files: list[Path], publish_dir: Path) -> list[Path]:
    publish_dir.mkdir(parents=True, exist_ok=True)
    published = []

    for file in files:
        target = publish_dir / file.name
        if copy_file_without_overwrite(file, target):
            published.append(target)

    return published


def copy_referenced_assets(
    files: list[Path],
    release_assets_dir: Path,
    publish_assets_dir: Path,
) -> list[Path]:
    asset_slugs = sorted(collect_asset_slugs(files))
    published = []

    for slug in asset_slugs:
        source = release_assets_dir / slug
        if not source.exists():
            continue

        target = publish_assets_dir / slug
        if copy_path_without_overwrite(source, target):
            published.append(target)

    return published


def copy_path_without_overwrite(source: Path, target: Path) -> bool:
    if source.is_dir():
        return copy_directory_without_overwrite(source, target)

    return copy_file_without_overwrite(source, target)


def copy_directory_without_overwrite(source: Path, target: Path) -> bool:
    target.mkdir(parents=True, exist_ok=True)
    copied = False

    for child in source.iterdir():
        child_target = target / child.name
        copied = copy_path_without_overwrite(child, child_target) or copied

    return copied


def copy_file_without_overwrite(source: Path, target: Path) -> bool:
    if target.exists():
        return False

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def collect_asset_slugs(files: list[Path]) -> set[str]:
    slugs = set()

    for file in files:
        post = frontmatter.load(file)
        slugs.update(ASSET_PATH_PATTERN.findall(post.content))

        for value in post.metadata.values():
            if isinstance(value, str):
                slugs.update(ASSET_PATH_PATTERN.findall(value))

    return slugs


def run_git_publish(base_dir: Path, content_type: str) -> GitResult:
    ensure_publish_git_repo(base_dir)
    run_git_command(base_dir, ["git", "add", "."])

    if not git_has_changes(base_dir):
        return GitResult(base_dir, committed=False, pushed=False, message="No changes to publish.")

    message = f"Publish {content_type}"
    run_git_command(base_dir, ["git", "commit", "-m", message])
    run_git_command(base_dir, ["git", "push"])
    ensure_clean_git_status(base_dir)
    return GitResult(base_dir, committed=True, pushed=True, message=message)


def ensure_publish_git_repo(base_dir: Path):
    result = run_git_command(base_dir, ["git", "rev-parse", "--show-toplevel"], check=False)
    output = combined_output(result)

    if result.returncode != 0:
        raise GitRepositoryError(base_dir, output)

    git_root = Path(result.stdout.strip()).resolve()
    if git_root != base_dir.resolve():
        raise GitRepositoryError(base_dir, f"Found parent git repository: {git_root}")


def ensure_clean_git_status(base_dir: Path):
    status = git_status(base_dir)
    if status:
        raise DirtyPublishRepositoryError(base_dir, status)


def git_status(base_dir: Path) -> str:
    result = run_git_command(base_dir, ["git", "status", "--porcelain"], check=False)
    if result.returncode != 0:
        raise GitCommandError(
            ["git", "status", "--porcelain"],
            base_dir,
            combined_output(result),
        )

    return result.stdout.strip()


def git_has_changes(base_dir: Path) -> bool:
    result = run_git_command(base_dir, ["git", "diff", "--cached", "--quiet"], check=False)
    return result.returncode == 1


def run_git_command(
    base_dir: Path,
    command: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            command,
            cwd=base_dir,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise GitCommandError(command, base_dir, str(error)) from error

    if check and result.returncode != 0:
        raise GitCommandError(command, base_dir, combined_output(result))

    return result


def combined_output(result: subprocess.CompletedProcess) -> str:
    return "\n".join(part for part in (result.stdout, result.stderr) if part).strip()


def run_jekyll_server(base_dir: Path, port: int) -> JekyllResult:
    try:
        subprocess.Popen(
            ["bundle", "exec", "jekyll", "serve", "--port", str(port)],
            cwd=base_dir,
        )
    except FileNotFoundError as error:
        raise JekyllCommandError(base_dir, str(error)) from error

    return JekyllResult(base_dir, port)
