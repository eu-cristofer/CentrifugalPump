# Design system

PumpFlow looks the way it does because of one file:
**[`pump/design/tokens.json`](../pump/design/tokens.json)**.  Every colour, font size, radius,
spacing step and canvas measure in the workbench, its charts and its reports is a named
token there.  Code uses only the names.

The same file feeds the **PumpFlow design-system artifact**, the browsable brand book.  It has
the shape the artifact reads, so the two are synced by copying it.

## Rules

1. **No literal values in code.**  No `#rrggbb`, no `QColor("…")` with a hex value, no matplotlib
   colour strings for brand colours.  Use a token:

   | Where | How |
   |---|---|
   | Qt stylesheet (`pumpflow/style.py` `APP_QSS`) | `@token-name` for colours, radii and spacing, `@fs-<text style>` for font sizes; filled in by `pump.design.render` |
   | Qt widgets and painting | `pumpflow.style.qcolor("token")`, or the names in `pumpflow.canvas.theme` |
   | matplotlib / pyqtgraph (library and workbench) | `pump.design.color("token")` |
   | HTML report CSS | `@token-name` through `render` |
   | layout margins | `pump.design.length("space-…")` |

2. **Say what a token is for.**  Every token has a `usage` note naming where it is used and,
   for text, its contrast on its background.
3. **Meet the contrast floors.**  Text 4.5:1 on its background (3:1 at 24 px and up); control
   borders, focus rings and icons 3:1.  Colours that must be told apart differ in lightness,
   not hue alone.
4. **Colour carries meaning, not decoration.**  `accent` is the only interactive colour.
   Status (`banner-*`, `ok-green`, `reject-red`, `amber`) always comes with a word (PASS, FAIL,
   unverified).  Port colours are reserved for their signal type.

`tests/test_design_tokens.py` enforces all four:
- no colour literal anywhere in `pump/` or `pumpflow/`;
- the file's shape, unique names and a usage note on every token;
- every alias resolves and every token is used;
- no unknown names in the stylesheet;
- a list of 35 text and control pairs checked against their floors.

## The families

| Family | Examples | Notes |
|---|---|---|
| **Surfaces** | `window-bg`, `canvas-bg`, `surface`, `surface-sunken`, `surface-muted`, `mono-bg` | Chrome sits on `surface`; docks and the welcome panel on `surface-sunken`. |
| **Text** | `body-text`, `subtle-text`, `field-label`, `unit-label`, `steel`, `selected-text` | `steel` is for uppercase section labels and table headers. |
| **Lines** | `border` (decorative hairline), `control-border` (inputs, checkboxes), `divider`, `gridline`, `grid-dot` | Separate with hairlines, not shadows; only nodes and dialogs cast a shadow (`node-shadow`). |
| **Headers** | `title-bg` (dialogs, processing nodes), `title-bg-source` (source nodes), `title-text`, `header-subtitle`, `header-button-*` | Dialog headers are always `title-bg`. |
| **Disabled** | `disabled-bg`, `disabled-text`, `disabled-border` | Inputs, checkboxes and field labels of a disabled row. Disabled text is exempt from the contrast floors. |
| **Interaction** | `check-mark` (tick on `accent`), `accent`, `accent-hover`, `hover-bg`, `menu-selected-bg`, `row-hover-bg`, `selection-bg`, `table-selection-bg`, `info-button` | |
| **Status** | `banner-{info,ok,warn,error}-{bg,text}`, `banner-ok-border`, `banner-error-border`, `verdict-idle-*`, `ok-green`, `reject-red`, `amber`, `warn-text` | `amber` is a canvas fill only; warning text uses `warn-text`. |
| **Ports and edges** | `port-rated-point`, `port-fluid-spec`, `port-test-point-set`, `port-corrected-curve`, `port-fitted-model`, `port-compliance-result`, `port-branch-bundle` (fallback), `port-ring`, `edge`, `edge-active` | One colour per signal type. |
| **Screen charts** | `chart-head`, `chart-power`, `chart-efficiency`, `chart-npsh`, `chart-npsha`, `chart-series-4…6`, `chart-ink`, `chart-tick`, `chart-grid`, `chart-frame`, `chart-cursor` | Head, power and efficiency keep the same colours in the Performance Plot, the Explore Chart and the report curve; the A/B comparison uses the same six colours, one per pump. |
| **Print charts** | `print-ink`, `print-grid-major`, `print-grid-minor`, `print-measured`, `print-test-point`, `print-limit`, `print-text` | The Annex M charts (Figures M.3 / M.4) are nearly monochrome, like the printed form. |
| **HTML report** | `report-text`, `report-heading`, `report-rule`, `report-head-bg`, … | |
| **Type** | text styles `body` 13 px, `subtitle` / `banner` / `unit` 12 px, `caption` 11 px, `section-label` 10 px bold, `verdict` 18 px, `welcome-title` 20 px, `node-title`, `node-body`, `mono-block` | One sans family (Segoe UI, then Inter, Helvetica Neue, Arial), resolved at start-up from what is installed. |
| **Spacing** | `space-control-y/x`, `space-row`, `space-banner-x`, `space-section`, `space-dialog-top/bottom/x`, `space-header-gap` | |
| **Radius** | `radius-check` 4 → `radius-control` 6 → `radius-banner` 7 → `radius-card` 8 → `radius-node` 9 → `radius-welcome` 10 | Corners grow with the size of the thing. |
| **Canvas** | `node-width` 196, `node-title-height` 30, `node-row-height` 22, `port-radius` 6, `canvas-grid` 26 | |

Font sizes are written in px (at 96 dpi).  The stylesheet hands them to Qt in **points at the
screen's own DPI** (`pumpflow.style._px_to_pt`).  A pixel-sized Qt font makes Windows warn
`QFont::setPointSize: Point size <= 0 (-1)`.

## Changing the look

- **Recolour something:** change its value in `tokens.json`.  That is the only edit: the stylesheet,
  canvas, charts and reports all follow.  Example: switching the accent from blue to teal is
  one line, `"accent"`, and the RatedPoint port, active edges, focus rings and head curves
  follow because they are aliases (`"{accent}"`) of it.
- **A new colour:** add a token with a usage note (and its contrast if it is text), use it by
  name, and add its text pair to `PAIRS` in `tests/test_design_tokens.py`.  A token no code uses
  fails the tests: delete it instead.
- **A new port type:** add `port-<signal>` and map it in `pumpflow/canvas/theme.py`
  `PORT_COLORS`.
- **See it:** `python -m pumpflow`; the charts appear in a report export
  (`python -m pumpflow.export_cli … --summary`).

## Contrast fixes made when the system was formalised (2026-11-17)

These pairs fell short in the first sync.  Each was darkened just enough to meet its floor,
keeping the hue:

| Token | Was | Now | On | Ratio |
|---|---|---|---|---|
| `unit-label` | `#8a96a3` | `#657281` | `surface` / `surface-sunken` | 3.0 → 4.9 / 4.5 |
| `placeholder` | `#a0aab4` | `{unit-label}` | `surface-sunken` | 2.2 → 4.5 |
| `steel` | `#5b7185` | `#566b7e` | `dock-title-bg` | 4.2 → 4.5 |
| `verdict-idle-text` | `#6b7785` | `#646f7d` | `banner-info-bg` | 4.1 → 4.5 |
| `control-border` (new; inputs used `border`, checkboxes `border-check`) | `#c3ccd6` / `#b6c0cb` | `#7d90a6` | `surface` | 1.6 / 1.9 → 3.3 |
| `info-button` | `#5b8def` | `{accent}` | `surface` | 3.2 → 5.2 |
| `warn-text` (Compliance "unverified" note) | `#b7791f` | `{banner-warn-text}` | `surface` | 3.6 → 6.1 |

`header-subtitle` on `title-bg-source` (3.4:1) was the sixth flagged pair.  It never occurs,
because dialog headers are always `title-bg`, so the documentation was corrected instead.

## The artifact

The design-system artifact (*PumpFlow*) presents this file as a browsable brand book.  After
changing `tokens.json`, re-sync it: its `project/tokens.json` is this file as is, and its README
is the brand book in prose.
