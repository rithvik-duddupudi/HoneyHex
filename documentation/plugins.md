# Third-party CLI plugins

HoneyHex loads optional Typer extensions from the **`honeyhex.plugins`** entry-point group.

## Registering a plugin

In your package’s **`pyproject.toml`** (or **`setup.cfg`**):

```toml
[project.entry-points."honeyhex.plugins"]
mypkg = mypkg.hex_plugin:register
```

The callable **`register(app: typer.Typer) -> None`** should attach commands or sub-apps to the main **`hex`** CLI.

## Caveat: Typer single-command mode

If the root Typer app would only expose one command, Typer may treat it as a single-command program. Plugins that add a second command avoid this; HoneyHex’s own CLI always defines many commands, so third-party commands attach as additional subcommands.

## Verification

After install, run **`hex --help`** and look for your command name.
