# mono_tools
mono_tools is a system to automate publishing and archiving at monointerferenz.

## Create/sync the virtual environment:

`uv sync`

## Usage
### Configuartion
- Set paths in the `configuration.yaml`
- Create/edit templates in /templates as `.j2` file.

### Create a new post
`uv run python -m mono_tools.main "Post Title"`