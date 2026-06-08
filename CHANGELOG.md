# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- **`pumpflow/welcome.py` — start-screen dialog** (`WelcomeDialog`)
  - Modal dialog shown over the main window on every launch via
    `QTimer.singleShot(0, _show_welcome)`.
  - Two-column layout: *Recent Projects* (left) and *Examples* (right).
  - Recent projects persisted across sessions via
    `QSettings("PumpFlow", "PumpFlow")`, key `"recentFiles"` (max 5 entries,
    missing paths silently skipped).  Module-level helpers `load_recent()` and
    `save_recent()` encapsulate all `QSettings` access.
  - Bundled examples resolved from `pumpflow/examples/` via the package
    `__file__` pointer so they work from both the source tree and installed
    wheels.
  - Footer buttons: **New empty canvas** · **Open file…** · **Skip**
    (Skip / close-with-× both fall back to `build_default_pipeline`,
    preserving the previous startup behaviour).
  - `result_action`, `result_doc`, `result_path` attributes carry the user's
    choice back to `MainWindow._show_welcome` without exposing Qt internals.

- **`pumpflow/examples/` — bundled example pipelines**
  - `single_pump_fat_hc.pumpflow` — light-hydrocarbon FAT example (SG 0.736,
    833 m³/h, 73 m, 1750 rpm); mirrors the existing `examples/sample_project.pumpflow`.
  - `water_pump_curve_report.pumpflow` — clean-water FAT example (SG 1.0,
    400 m³/h, 100 m, 1480 rpm, 6 test points); produces a smooth polynomial
    curve, compliance passes, and exercises the full 7-node Report Export
    flow end-to-end.

- **`pumpflow/app.py` — welcome integration and project-load helper**
  - `MainWindow._show_welcome()` — dispatches on `WelcomeDialog.result_action`
    to load a project, start empty, or fall back to the default pipeline.
  - `MainWindow._load_project(doc, path=None)` — single place that calls
    `scene.load_dict`, resets the view, marks clean, registers the path in
    recent files, and updates the status bar.  Used by both `_show_welcome`
    and `open_project`.

- **`pumpflow/style.py` — welcome dialog styles**
  - New selectors: `#WelcomeDialog`, `#WelcomeHeader`, `#WelcomeTitle`,
    `#WelcomeSubtitle`, `#WelcomeContent`, `#WelcomePanel`,
    `#WelcomeSectionLabel`, `#WelcomePlaceholder`, `#WelcomeDivider`,
    `#WelcomeFooter`, `#RecentItem`, `#ExampleItem`, `#ExampleDesc`.
    All colours reuse the existing palette tokens.

- **`pumpflow/app.py` — unsaved-changes guard**
  - `MainWindow._dirty` (`bool`) and `MainWindow._current_path` (`Path | None`)
    instance variables track whether the canvas has changes not written to disk
    and the path of the last saved/opened file respectively.
  - `MainWindow._mark_dirty()` — sets `_dirty = True` and appends ` *` to the
    window title as a persistent visual cue.
  - `MainWindow._mark_clean()` — clears `_dirty` and strips the ` *` suffix.
  - `MainWindow._maybe_save()` — modal **Save / Discard / Cancel** guard called
    before any destructive canvas replacement.  Returns `False` if the user
    cancels, keeping the current project intact.
  - `MainWindow.new_project()` — **File > New (empty canvas)** (`Ctrl+N`):
    calls `_maybe_save()`, then loads an empty `{"nodes": [], "edges": []}` graph.
    Replaces the old behaviour that re-built the default pre-wired pipeline.
  - `MainWindow.closeEvent()` — intercepts the window-close event to call
    `_maybe_save()` so unsaved work is never silently lost.

- **`pumpflow/app.py` — save/open improvements**
  - `save_project` now pre-fills the file-picker with `_current_path` when a
    project has already been saved, and calls `_mark_clean()` on success.
  - `open_project` now guards unsaved changes via `_maybe_save()` before
    replacing the canvas, and calls `_mark_clean()` after a successful load.
  - `_on_dialog_change` now calls `_mark_dirty()` so edits made through node
    property dialogs are correctly reflected in the dirty state.

- **`pumpflow/canvas/scene.py` — graph-change signals**
  - `GraphScene.add_node()` now emits `graph_changed` after inserting a node so
    `MainWindow` can track mutations that originate inside the scene.
  - `GraphScene.connect_ports()` now emits `graph_changed` after a successful
    port connection for the same reason.

### Changed

- **File > New** menu item renamed from *"New pipeline"* to *"New (empty canvas)"*
  and now calls `new_project()` instead of `build_default_pipeline()`.
- **`open_project`** body delegated to `_load_project`; no behaviour change.
- **`pyproject.toml`** — added `[tool.setuptools.package-data]` so
  `pumpflow/examples/*.pumpflow` files are included in source distributions
  and wheels.

---

## [0.1.0] — initial release

- Headless `pump` library: Pint-based units, `Fluid`, `TestPoint`,
  `PerformanceCurve`, API 610 compliance checker, `.docx` report generation.
- `pumpflow` visual workbench: PySide6 node canvas, seven workflow nodes,
  `.pumpflow` project persistence, default pre-wired pipeline.
