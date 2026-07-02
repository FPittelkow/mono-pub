from pathlib import Path

import frontmatter

from mono_pub.process.compile import compile_draft
from mono_pub.process.release_config import get_release_config, path_key_for
from mono_pub.process.validate import missing_required_fields


class ReleaseError(Exception):
    pass


class MissingRequiredFieldsError(ReleaseError):
    def __init__(self, path: Path, fields: list[str]):
        self.path = path
        self.fields = fields
        super().__init__(f"Missing {fields}: {path}")


class ExistingReleaseError(ReleaseError):
    def __init__(self, path: Path):
        self.path = path
        super().__init__(f"Draft {path} already exists.")


def release_type(config: dict, content_type: str) -> list[Path]:
    path_key = path_key_for(content_type)
    release_config = get_release_config(config)

    return release_files(
        Path(config["drafts_path"][path_key]),
        Path(config["releases_path"][path_key]),
        Path(config["assets_path"][path_key]),
        release_config,
        content_type,
    )


def release_files(
    drafts_dir: Path,
    releases_dir: Path,
    assets_dir: Path,
    release_config: dict,
    content_type: str,
) -> list[Path]:
    drafts = list(drafts_dir.glob("*.md"))
    marked = [path for path in drafts if is_marked_for_release(path)]

    return [
        release_draft(path, releases_dir, assets_dir, release_config, content_type)
        for path in marked
    ]


def is_marked_for_release(path: Path) -> bool:
    post = frontmatter.load(path)
    return post.metadata.get("release") is True


def release_draft(
    path: Path,
    target_dir: Path,
    assets_dir: Path,
    release_config: dict,
    content_type: str,
) -> Path:
    post = frontmatter.load(path)
    missing = missing_required_fields(post, release_config, content_type)

    if missing:
        raise MissingRequiredFieldsError(path, missing)

    compiled = compile_draft(post, path, assets_dir, release_config)

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name

    if target.exists():
        raise ExistingReleaseError(target)

    target.write_text(frontmatter.dumps(compiled), encoding="utf-8")
    path.unlink()

    return target
