# tk-blender

A Shotgun Pipeline Toolkit (sgtk) engine for Blender. It integrates Blender with the Shotgun/ShotGrid ecosystem so artists can manage files, load/publish assets, and track context — all from within Blender.

## Tech Stack

- **Python 3** throughout (required by Blender 2.8+)
- **bpy** — Blender Python API for scene operations and event hooks
- **sgtk / tank** — Shotgun Toolkit core (`tk-core` ≥ 0.18.8)
- **PySide2** — Qt UI for menus, dialogs, and the integrated event loop
- **pre-commit** — code quality gates (black + flake8); see `.flake8` and `.pre-commit-config.yaml`

## Key Directories

| Path | Purpose |
|---|---|
| `engine.py` | `BlenderEngine` — core engine lifecycle, app handlers, context switching |
| `startup.py` | `BlenderLauncher` — launches Blender with toolkit env vars |
| `startup/bootstrap.py` | Deserializes context and bootstraps the engine inside Blender |
| `python/tk_blender/menu_generation.py` | `MenuGenerator` + `Callback` — builds the Shotgun menu from registered commands |
| `resources/scripts/startup/` | Blender addon scripts: Qt event loop integration, menu operators |
| `hooks/` | DCC-specific implementations for each integrated app (workfiles, publish, loader, etc.) |
| `config/env/` | Per-context YAML configs declaring which apps are active |
| `config/env/includes/settings/` | Per-app configuration blocks referenced by env configs |
| `info.yml` | Engine metadata, supported Blender versions, and config schema |

## Build / Lint Commands

```bash
# Lint
flake8

# Format
black .

# Run all pre-commit hooks against staged files
pre-commit run

# Run against all files (e.g., after adding new hooks)
pre-commit run --all-files
```

There is no automated test suite. Testing is done manually via Shotgun Desktop.

## Additional Documentation

Check these files when working on the relevant areas:

| Topic | File |
|---|---|
| Architectural patterns, design decisions, conventions | `.claude/docs/architectural_patterns.md` |
