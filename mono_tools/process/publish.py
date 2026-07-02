from dataclasses import dataclass
from pathlib import Path
import re
import shutil

import frontmatter

from mono_tools.process.release_config import path_key_for

ASSET_PATH_PATTERN = re.compile(r"assets/([^/\s\"')]+)")


@dataclass
class PublishResult:
    content_type: str
    files: list[Path]
    asset_dirs: list[Path]


def publish_type(config: dict, content_type: str) -> PublishResult:
    path_key = path_key_for(content_type)

    return publish_files(
        content_type,
        Path(config["releases_path"][path_key]),
        Path(config["assets_path"][path_key]),
        Path(config["publish_path"][path_key]),
        Path(config["publish_assets_path"][path_key]),
    )


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
        shutil.copy2(file, target)
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
        shutil.copytree(source, target, dirs_exist_ok=True)
        published.append(target)

    return published


def collect_asset_slugs(files: list[Path]) -> set[str]:
    slugs = set()

    for file in files:
        post = frontmatter.load(file)
        slugs.update(ASSET_PATH_PATTERN.findall(post.content))

        for value in post.metadata.values():
            if isinstance(value, str):
                slugs.update(ASSET_PATH_PATTERN.findall(value))

    return slugs
