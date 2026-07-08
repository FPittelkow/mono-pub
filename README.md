# mono-pub
mono-pub is a tool for publishing at monointerferenz.
It offers a command line interface and a optional terminal based GUI.

It prepares content to be published via Jekyll.

## Installation

### Requirements

* Python 3.13 or newer
* uv installed

Clone the repository

```bash
git clone <repository-url>
cd mono-pub
```

Setup the environment

Install all dependencies including the optional TUI:

```bash
uv sync --all-extras
```

### CLI usage

**During development:**

```bash
uv run mono-pub --help
```

Example:

```bash
uv run mono-pub new post "My first post"
```

### Install the CLI globally (optional)

```bash
uv tool install -e ".[tui]"
```

**Than it can be called with:**

```bash
mono-pub --help
mono-pub tui
```

**Update**

After changes in the repository:

```bash
git pull
uv sync --all-extras
```

If the tool was installed globally and metadata has changes (Entry Points, dependencies etc.):

```bash
uv tool install -e ".[tui]" --reinstall
```

## Usage

## Create a new post / project / music:
The tool offers three different types of content:
- **posts** are all purpose articles.
- **projects** are artworks to be presented in an online portfolio.
- **music** Are a special type of project.

```bash
mono-pub new post “My first post”
mono-pub new project “My first post”
mono-pub new music “My first music”
```

## list / open
``mono-list draft`` lists all content in the draft status.
``mono-list release`` lists all content that have gone through the release process

``mono-pub open post`` opens the draft folder in the configured editor. (Projects ans music follow the same pattern)

## Release
Drafts marked ``release: true`` in the frontmatter can be released. They will be verified and paths and links will be set for deployment. Assets get copied to the assets folder respectively. Frontmatter will be stripped down.

## Publish
``mono-pub publish all`` will be send all files to the server via git. It is also possible to publish only post, projects and music. Use ``mono-pub publish post`` etc.

- ``--no-git`` can be used to skip git operations.
- ``--git`` only runs git add / commit / push.
- ``--dry-run`` can be used to simulate the publish process through a local Jekyll server.