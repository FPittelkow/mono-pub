from pathlib import Path
import yaml

PATH_KEYS = ("templates_path",)
PATH_GROUP_KEYS = (
    "drafts_path",
    "release_path",
    "releases_path",
    "assets_path",
    "publish_base",
    "publish_path",
    "publish_assets_path",
)


def _resolve_path(path: str, base_dir: Path) -> str:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = base_dir / resolved
    return str(resolved)


def _resolve_config_paths(config: dict, base_dir: Path) -> dict:
    for key in PATH_KEYS:
        if key in config:
            config[key] = _resolve_path(config[key], base_dir)

    for key in PATH_GROUP_KEYS:
        paths = config.get(key, {})
        for path_key, path in paths.items():
            paths[path_key] = _resolve_path(path, base_dir)

    return config


def load_config(path: str = "configuartion.yaml"):
    config_path = Path(path).expanduser().resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"{config_path} does not exist")

    with config_path.open("r", encoding="utf-8") as file:
        return _resolve_config_paths(yaml.safe_load(file) or {}, config_path.parent)
