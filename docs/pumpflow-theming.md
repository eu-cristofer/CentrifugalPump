# pumpflow theming — editing the color scheme

pumpflow ships a single light, industrial blue/steel look. This guide explains
**where the colors live** and **how to change them**.

## The two sources of color

pumpflow's appearance comes from two files, and the split is not arbitrary:

| File | What it is | What it controls |
| --- | --- | --- |
| [`pumpflow/style.py`](../pumpflow/style.py) | `APP_QSS`, a Qt **stylesheet** (QSS) string applied app-wide in [`app.py`](../pumpflow/app.py) via `app.setStyleSheet(APP_QSS)` | All standard **widget** chrome: window/menu/toolbar/status-bar, dialogs, inputs, buttons, tables, banners, scrollbars, the welcome dialog |
| [`pumpflow/canvas/theme.py`](../pumpflow/canvas/theme.py) | Python `QColor`/`QFont` constants + layout metrics | The **canvas drawing**: node bodies/titles, ports, edges, the dotted grid — anything painted by custom `QGraphicsItem`s |

**Why two?** QSS only reaches real `QWidget`s. The canvas nodes, ports, and edges
are custom-painted `QGraphicsItem`s, which QSS cannot style — they read their
colors from `theme.py` at paint time. So widget chrome → `style.py`; canvas
graphics → `theme.py`.

## What you see on screen → what to edit

| You want to change… | Edit | Key |
| --- | --- | --- |
| App / window background | `theme.py` | `WINDOW_BG` (and `#eef1f4` in `style.py`) |
| Canvas background & grid dots | `theme.py` | `CANVAS_BG`, `GRID_DOT`, `GRID_DOT_STRONG` |
| Node body / alt row / border | `theme.py` | `NODE_BG`, `NODE_BG_ALT`, `NODE_BORDER` |
| Node title bar (steel) | `theme.py` | `TITLE_BG`, `TITLE_BG_SOURCE`, `TITLE_TEXT` |
| Selected-node outline | `theme.py` | `NODE_BORDER_SEL` |
| Edges (idle / active) | `theme.py` | `EDGE`, `EDGE_ACTIVE` |
| Port color per signal type | `theme.py` | `PORT_COLORS` dict |
| Dialog header bar / title text | `style.py` | `#DialogHeader`, `#DialogTitle`, `#DialogSubtitle` |
| Inputs (line edit / spin / combo) | `style.py` | `QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox` rules |
| Primary / tool buttons | `style.py` | `#PrimaryButton`, `#ToolButton` |
| Status banners (info/ok/warn/error) | `style.py` | `#Banner[kind="…"]` |
| Compliance verdict banner | `style.py` | `#VerdictBanner[verdict="pass|fail|idle"]` |
| Tables | `style.py` | `QTableWidget`, `QHeaderView::section` |
| Welcome / splash dialog | `style.py` | `#Welcome*` rules |

In `style.py`, selectors beginning with `#` target a widget's Qt **objectName**
(set in the widget code as `objectName="…"`); selectors without `#` target a Qt
**class** (e.g. `QPushButton`). Colors are plain hex literals.

## ⚠️ The shared accent color lives in BOTH files

The industrial blue accent **`#2f6fb0`** is used on both the widget side and the
canvas side. To re-key the whole app to a different accent you must edit **both**
files — changing only one leaves the UI half-recolored:

- `theme.py`: `ACCENT`, `NODE_BORDER_SEL`, `EDGE_ACTIVE`, and the `RatedPoint`
  entry in `PORT_COLORS` are all `#2f6fb0`.
- `style.py`: every `#2f6fb0` occurrence (focus borders, hover states,
  `#PrimaryButton`, `#ToolboxItem:hover`, menu selection accents, etc.), plus the
  darker hover shade `#2a64a0`.

## Worked example — switch the accent from blue to teal

Say you want a teal accent `#2f9b8e` (hover `#268074`).

1. In [`theme.py`](../pumpflow/canvas/theme.py), set:
   ```python
   NODE_BORDER_SEL = QColor("#2f9b8e")
   ACCENT = QColor("#2f9b8e")
   EDGE_ACTIVE = QColor("#2f9b8e")
   PORT_COLORS = {
       "RatedPoint": QColor("#2f9b8e"),
       ...
   }
   ```
2. In [`style.py`](../pumpflow/style.py), replace every `#2f6fb0` with `#2f9b8e`
   and every `#2a64a0` with `#268074`. (A find-replace across `APP_QSS` is the
   fastest path; there are no other meanings for those two strings.)
3. Re-run the app (see below). Node selection, edges, ports, focus rings, buttons,
   and menu highlights all move to teal together.

## Adding a color for a new signal/port type

Port colors are keyed by the signal **dataclass name** from
[`pumpflow/signals.py`](../pumpflow/signals.py). To color a new signal type, add an
entry to `PORT_COLORS` in `theme.py`:

```python
PORT_COLORS = {
    "RatedPoint": QColor("#2f6fb0"),
    ...
    "MyNewSignal": QColor("#a05fb0"),
    "*": QColor("#7a8694"),   # fallback for unmapped types
}
```

`port_color(signal_type)` falls back to the `"*"` entry for any unmapped name.

## Metrics (not colors, but in the same file)

`theme.py` also holds canvas **layout** constants — `NODE_W`, `TITLE_H`, `ROW_H`,
`PORT_R`, `NODE_RADIUS`, `GRID_SIZE` — and the `title_font()` / `body_font()` /
`mono_font()` helpers. Adjust these to change node size, corner rounding, or grid
spacing.

## Seeing your changes

The stylesheet and palette are read **once at startup**; there is no hot-reload.
After editing either file, restart the workbench:

```bash
python -m pumpflow
```
