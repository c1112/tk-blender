# Architectural Patterns

## Engine Lifecycle (Template Method)

`BlenderEngine` extends sgtk's `Engine` base class and must implement lifecycle hooks in order:

`pre_app_init()` → `init_engine()` → `post_app_init()` → `post_context_change()`

See `engine.py:219`. The base class drives the sequence; each method handles a distinct phase (Qt app setup, handler registration, menu creation, etc.).

## Hook Pattern (Strategy)

DCC-specific behaviour is isolated in hooks that inherit from sgtk base classes:

- `HookBaseClass` / `Hook` — base provided by `tk-core`
- Each hook lives under `hooks/<app-name>/` and is named per convention (e.g., `scene_operation_tk-blender.py`)
- Config files (`config/env/includes/settings/tk-*.yml`) wire hooks to apps; the engine discovers them automatically

Examples:
- `hooks/tk-multi-workfiles2/scene_operation_tk-blender.py:32` — `SceneOperation(HookClass)`
- `hooks/tk-multi-loader2/tk-blender_actions.py:60` — `BlenderActions(HookBaseClass)`
- `hooks/tk-multi-publish2/basic/collector.py:29` — `PublishCollector(HookBaseClass)`

## Dynamic Command Registry → Menu (Factory)

Apps register named commands on the engine. `MenuGenerator` (`python/tk_blender/menu_generation.py:68`) iterates `engine.commands`, groups them by `app_instance`, and builds `QMenu` submenus at runtime. No menu items are hardcoded.

Command grouping loop: `engine.py:557-565`.

## Deferred Callback Execution

`Callback` (`menu_generation.py:32`) wraps every menu action with `QtCore.QTimer.singleShot(0, ...)`. This defers execution until after the current Qt event loop tick, preventing crashes caused by Blender tearing down the menu while a callback is still on the stack.

```
menu click → Callback.__call__() → QTimer.singleShot(0, _execute_within_exception_trap)
                                        └─ wraps in try/except, logs via engine.logger
```

## Qt ↔ Blender Event Loop Integration

Blender has no native Qt event loop. `QtWindowEventLoop` (`resources/scripts/startup/Shotgun_menu.py:90`) is a Blender modal operator driven by a `TIMER` event that calls `QApplication.processEvents()` each tick. The operator exits when all Qt windows are closed.

## Observer: Blender Scene Event Handlers

`engine.py:88-216` registers persistent Blender handlers for file load/save:

```python
bpy.app.handlers.load_post.append(on_scene_event_callback)
bpy.app.handlers.save_post.append(on_scene_event_callback)
```

`@persistent` keeps handlers alive across scene reloads. Each event calls `refresh_engine()`, which extracts a new sgtk context from the file path and calls `engine.change_context()`.

## Three-Layer Configuration

Settings cascade across three layers:

1. **`info.yml`** — declares valid settings and their types/defaults for the engine
2. **`config/env/<context>.yml`** — enables apps per pipeline context (asset_step, shot_step, etc.)
3. **`config/env/includes/settings/tk-*.yml`** — configures individual apps (hooks, templates, menu favourites)

Access at runtime: `self.get_setting("key")` in `engine.py` (e.g., `engine.py:375`).

## Launcher / Adapter Pattern

`BlenderLauncher` (`startup.py:25`) extends `SoftwareLauncher` to adapt Blender's executable and environment to the generic toolkit launch interface. It:
- Defines `EXECUTABLE_TEMPLATES` per OS
- Serializes the sgtk context into `SGTK_CONTEXT` env var
- Injects `SGTK_ENGINE`, `PYTHONPATH`, and `BLENDER_USER_SCRIPTS` so `startup/bootstrap.py` can reconstitute the engine inside Blender

## Error Handling Convention

Two tiers used throughout:

1. **Silent + log**: wrap in `try/except`, call `engine.logger.exception(...)`, allow execution to continue (common in bootstrap and event callbacks)
2. **User-visible + log**: catch, log, then show `QtGui.QMessageBox.critical(...)` for errors the user must know about (e.g., `engine.py:94-110`)

Never swallow exceptions silently — always log the full traceback.

## Singleton Qt Application

A single `QApplication` is created once and reused for the session (`engine.py:462`). The engine stores it as `self._qt_app`. All dialogs and menus share this instance.

## Naming Conventions

- Classes: `PascalCase` — `BlenderEngine`, `MenuGenerator`, `BlenderLauncher`
- Methods/functions: `snake_case` — `refresh_engine()`, `setup_app_handlers()`
- Module-level constants: `UPPER_SNAKE_CASE` — `ENGINE_NAME`, `MIN_COMPATIBILITY_VERSION`, `SHOW_COMP_DLG`
- Hook directories match app instance names: `hooks/tk-multi-loader2/`, `hooks/tk-multi-publish2/basic/`
- Properties use `@property` with snake_case: `context_change_allowed`, `host_info`
