# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

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

---

## [0.1.0] — initial release

- Headless `pump` library: Pint-based units, `Fluid`, `TestPoint`,
  `PerformanceCurve`, API 610 compliance checker, `.docx` report generation.
- `pumpflow` visual workbench: PySide6 node canvas, seven workflow nodes,
  `.pumpflow` project persistence, default pre-wired pipeline.
