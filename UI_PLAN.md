# UI plan — porting `pump_api610_performance 1.ipynb` into the `centrifugal-pump` library

> Source notebook: [examples/pump_api610_performance 1.ipynb](examples/pump_api610_performance%201.ipynb)
> Library entry points: [pump/point.py](pump/point.py), [pump/performance_curve.py](pump/performance_curve.py), [pump/utilities/unit_conversion.py](pump/utilities/unit_conversion.py), [pump/utilities/report.py](pump/utilities/report.py)
> Date: 2026-05-21

---

## 1 · UX captured from the notebook

The notebook bundles **three tkinter windows** that together form the FAT (Factory Acceptance Test) workflow. They are the reference UX to preserve.

### 1.1 Main input window — `PumpDataDialog`

A single resizable window with these regions, top to bottom:

| Region | Widgets | Notes |
|---|---|---|
| **Pressure unit** | Radio: `kgf/cm²` / `bar` | Drives the head-from-pressure conversion live (`pressure_to_head`). |
| **Applicable standard** | Combobox: `API610 (12a) / ISO 13709 + N-553`, `ASME B73.1/B73.2 + N-906`, `ISO 5199 + N-906` | Picks the tolerance criteria set used downstream. |
| **Parallel operation** | Checkbox | Enables the `H_shutoff ≥ 110 % × H_rated` extra criterion. |
| **Rated point (data sheet)** | 8 entry fields: TAG, Q [m³/h], H [m], N [rpm], P [kW], relative density [-], nominal viscosity [cSt], H_shutoff [m] | Laid out in a 2-column grid for compactness. |
| **Test points table** | Per-row: Q [m³/h], P_suc, P_dis, T_water [°C], computed Head [m] (live), Power [kW], N [rpm] | Head is auto-computed from `(p_dis-p_suc)` × unit × water-density(T); recomputes when the pressure unit changes. |
| **Action bar** | `Importar dados` · `Exportar dados` · `Calcular e gerar gráficos` · `Fechar` | Add/remove row buttons live under the table. |

### 1.2 Curves window — `_show_plots_window`

A maximized horizontal `PanedWindow` opened on "Calcular":
- Left pane (weight 3): three stacked matplotlib subplots — Q×H, Q×P, Q×η — with the polynomial fit (blue solid), natural cubic spline (green dashed), corrected test points (black dots), and red dotted lines at the rated point.
- Right pane (weight 2): the results table (see next), in the same window.

The native matplotlib navigation toolbar (zoom, pan, save PNG) is on top of the canvas.

### 1.3 Results window — `_show_results_window`

A 6-column table:
`Parâmetro | Nominal | Predito | Desvio | Tolerância | Parecer`

with rows for polynomial **and** spline predictions of `H`, `P`, `η`, `H_shutoff` (plus the `H_shutoff ≥ 110 %` row when parallel operation is on). Pass/fail cells are tinted green/red. Below the table:
- Static checklist of extra acceptance criteria (noise ≤ 85 dB, no visible seal leak).
- For API 610: a vibration-criteria block.
- Action bar: `Salvar dados` (JSON), `Exportar Word` (HTML-as-`.doc` with the chart embedded base64), `Fechar`.

### 1.4 Persistence shapes (already designed by the notebook)

**Input JSON** (round-trips the form — see [examples/Teste B-432201C 28abr26 (1).json](examples/Teste%20B-432201C%2028abr26%20(1).json)):

```json
{
  "unit": "bar",
  "standard": "API610 (12a ed.) / ISO 13709 + N-553",
  "parallel_operation": false,
  "rated": { "tag": "...", "q_m3h": "...", "head_m": "...", "n_rpm": "...",
             "power_kw": "...", "dens_rel": "...", "visc_nom_cst": "...",
             "head_shutoff": "..." },
  "points": [{ "q": "...", "p_suc": "...", "p_dis": "...", "temp_c": "...",
               "head": "...", "power": "...", "n_rpm": "..." }, ...]
}
```

**Result JSON** (signed-off report — `_build_report_payload`):

```json
{
  "bomba": "TAG",
  "norma": "...",
  "ponto_nominal": { ... },
  "predicoes_ponto_nominal": { "head_poly_m": ..., "head_spline_m": ..., ... },
  "tolerancias": { "head": 0.03, "power": ..., "eff": ..., "shutoff": ... },
  "operacao_paralelo": false,
  "shutoff_min_paralelo_m": null,
  "criterios_adicionais": { "ruido": "...", "vazamento_selo": "...",
                            "vibracao_api610": [...] },
  "resultados": [{ "parametro": "...", "nominal": ..., "predito": ...,
                   "desvio": ..., "tolerancia": ..., "parecer": "..." }]
}
```

Both shapes are **load-bearing** — they're already in use on disk and must stay backward-compatible.

---

## 2 · Math engine decision (and why)

**Decision: use the library as the canonical engine; promote the notebook's spline + multi-standard tolerances into the library.**

Justification:

| Concern | Library path (Pint + numpy) | Notebook path (stdlib only) |
|---|---|---|
| Unit safety | `quantity_factory` rejects raw floats → cannot mix bar/kgf accidentally. | Implicit floats; conventions live in variable names. |
| Polynomial / power fits | `numpy.polynomial`, already cached in `PerformanceFitter`. | Hand-rolled Gauss + power basis (works, but reinvents). |
| Affinity scaling | `PerformanceCurve.to_speed` / `.to_fluid` return new instances. | Per-point inline. |
| Reporting | `ReportGenerator` already produces `.docx` from `.po`-localized templates. | Builds HTML and saves it as `.doc`. |
| Future viscosity correction | Single place to add it (TODO already on the README). | Would need to be added in both engines. |
| Packaging size | numpy + pint add ~30 MB to PyInstaller bundles. Acceptable for a desktop FAT tool. | Smallest possible. |

What's missing from the library and must be added:

1. **`CubicSplineFitter`** — a natural cubic spline (notebook's `NaturalCubicSpline`) sitting next to `PerformanceFitter` so the UI can show poly + spline side by side. Use `scipy.interpolate.CubicSpline(..., bc_type="natural")` to avoid hand-rolling.
2. **`PerformanceChecker` multi-standard support** — extend `_norm_criteria` from the notebook (`API610` / `ASME B73` / `ISO 5199`) into `PerformanceChecker`. Today it only encodes API 610.
3. **Parallel-operation criterion** — `H_shutoff ≥ 1.10 × H_rated` switch.
4. **Pressure-derived head helper** — `TestPoint.from_pressures(p_suc, p_dis, unit, temp_c)` using the notebook's water-density polynomial; today this lives only in the notebook.
5. **Viscosity correction factors** (already a README TODO) — `viscosity_correction_factors(nu_cst)` returning `(f_head, f_power, f_eff)`.
6. **Fix [`Point.outlet_pressure`](pump/point.py)** — currently a broken stub calling `quantity_factory()` with no args. Either delete `Point` or wire it correctly.

These are pure-library changes, no UI involved, and they unblock everything below.

---

## 3 · Recommended stack

The user's requirement is a **single Python codebase** that ships as:
- a **single-file executable** for offline desktop use during FAT,
- a **web app** for shared/internal access.

### 3.1 Stack options compared

| Stack | Web | Desktop exe | Effort | Native feel | Notes |
|---|---|---|---|---|---|
| **A. NiceGUI** (recommended) | ✅ FastAPI under the hood | ✅ `ui.run(native=True)` wraps PyWebView; PyInstaller-supported | Low | Good (system webview) | One codebase, Python-only. Built-in `ui.plot` (matplotlib), `ui.table`, `ui.upload`, dialogs. |
| **B. FastAPI + React/Vue + PyWebView** | ✅ | ✅ PyWebView loads bundled JS | Med-High | Best | Most flexible UI, but two languages, two build steps, larger bundle. |
| **C. Streamlit** | ✅ | ⚠️ Possible via stlite/Electron, but not first-class | Lowest | Web-only | Trivial to prototype, hard to ship as native exe. |
| **D. Dash / Plotly** | ✅ | ⚠️ via PyWebView, but Dash needs its server running | Low-Med | Good | Excellent for engineering plots; less ergonomic for forms. |
| **E. PySide6 (Qt) + FastAPI** | ✅ (separate service) | ✅ (PyInstaller) | High | Native | Two UIs to maintain — exactly what we're trying to avoid. |
| **F. Reflex (formerly Pynecone)** | ✅ | ⚠️ exp. desktop | Low | Good | Python-only React; younger ecosystem; desktop story still maturing. |

### 3.2 Recommendation: **A — NiceGUI + matplotlib + PyInstaller**

Why:
- **Single code path for both targets.** `nicegui.ui.run(...)` serves the same app as a browser-facing FastAPI server (default) or a native window (`native=True` → PyWebView). No conditional UI code.
- **Library compatibility.** `pump` already produces matplotlib figures (`PerformanceCurve.plot_performance_curve`); NiceGUI embeds them directly via `ui.matplotlib()` / `ui.pyplot()`.
- **PyInstaller-friendly.** NiceGUI documents a single-file build, and the `pump` library is pure-Python plus numpy/pint/python-docx (all PyInstaller-compatible).
- **Reuses existing reporting.** `ReportGenerator` (python-docx + gettext) is already wired up — the UI just calls it and offers a download.
- **Localization fit.** The notebook UI is Portuguese; the library has `en`/`pt` `.po` catalogs — NiceGUI strings can pull from the same gettext instance.

Trade-offs accepted:
- NiceGUI does not yet have a polished `Treeview`-style spreadsheet; the test-points editor will use `ui.table` in editable mode plus an "add row" button (close to the notebook's experience).
- The native window uses the system's webview (Edge WebView2 on Windows, WebKit on macOS, WebKitGTK on Linux). For Windows offline FAT machines, the installer must ensure WebView2 is present (Windows 11 ships it; Windows 10 may need the redistributable).

### 3.3 Final concrete stack

| Layer | Choice |
|---|---|
| Core math + units | `pump` package (Pint + numpy), extended per §2 |
| HTTP/API layer | `FastAPI` (re-used through NiceGUI), so the same endpoints serve both UI and any future scripting client |
| UI framework | `NiceGUI` (web + native via PyWebView) |
| Plots | `matplotlib` via `ui.pyplot()` (zoom toolbar) — alternative `plotly` via `ui.plotly()` for interactivity |
| Reports | `python-docx` (`pump.utilities.report.ReportGenerator`) |
| JSON I/O | `pydantic` v2 models for validation + round-tripping |
| Localization | Existing `pump/utilities/locales/{en,pt}` `.po` files |
| Packaging — desktop | `PyInstaller` one-file build; ship platform-specific binaries from CI (`windows-latest`, `macos-latest`, `ubuntu-latest`) |
| Packaging — web | `Dockerfile` running `python -m pump.app` on `uvicorn`, behind a reverse proxy |
| Tests | `pytest` for engine, `playwright` for UI smoke tests against the same NiceGUI app in headless mode |

---

## 4 · Target package layout

```
pump/
├── __init__.py
├── point.py                  (existing — fix Point.outlet_pressure)
├── performance_curve.py      (existing — add CubicSplineFitter, multi-standard checker)
├── corrections.py            (NEW — affinity laws, viscosity factors, water density)
├── io/
│   ├── __init__.py
│   ├── schemas.py            (NEW — pydantic models for input/result JSON)
│   ├── json_io.py            (NEW — load_input / dump_input / load_result / dump_result)
│   └── legacy.py             (NEW — translates the notebook's "dens_rated" / decimal-comma JSON)
├── app/                      (NEW — UI lives here)
│   ├── __init__.py
│   ├── __main__.py           (entry point: `python -m pump.app`)
│   ├── server.py             (NiceGUI app factory, mode flag)
│   ├── pages/
│   │   ├── classic.py        (one-window notebook-faithful layout)
│   │   ├── wizard.py         (modernized stepper: Setup → Points → Curves → Report)
│   │   └── shared.py         (widgets reused by both)
│   └── components/
│       ├── rated_form.py
│       ├── points_table.py
│       ├── curves_panel.py
│       └── results_panel.py
├── templates/                (existing .docx)
└── utilities/                (existing)
tests/
├── test_corrections.py
├── test_json_io.py
├── test_performance_curve.py
└── ui_smoke/test_classic_flow.py
build/
├── pump-desktop.spec         (PyInstaller spec)
└── Dockerfile                (web image)
```

---

## 5 · JSON export / import — concrete plan

Two schemas, two endpoints, three files on disk are involved.

### 5.1 Schemas (`pump/io/schemas.py`)

```python
class RatedInput(BaseModel):
    tag: str
    q_m3h: Decimal
    head_m: Decimal
    n_rpm: Decimal
    power_kw: Decimal
    dens_rel: Decimal
    visc_nom_cst: Decimal | None = None
    head_shutoff: Decimal | None = None

class TestPointInput(BaseModel):
    q: Decimal
    p_suc: Decimal
    p_dis: Decimal
    temp_c: Decimal
    head: Decimal | None = None  # auto-computed from p_suc/p_dis if absent
    power: Decimal
    n_rpm: Decimal

class PumpInputDocument(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    unit: Literal["bar", "kgf/cm²"]
    standard: Literal[
        "API610 (12a ed.) / ISO 13709 + N-553",
        "ASME B73.1 / B73.2 + N-906",
        "ISO 5199 + N-906",
    ]
    parallel_operation: bool = False
    rated: RatedInput
    points: list[TestPointInput]

class ResultRow(BaseModel):
    parametro: str
    nominal: Decimal | None
    predito: Decimal | None
    desvio: Decimal | None
    tolerancia: Decimal | None
    parecer: Literal["✅ APROVADO", "❌ REPROVADO", "N/A"]

class PumpResultDocument(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    bomba: str
    norma: str
    ponto_nominal: dict
    pontos_corrigidos: list[dict]
    predicoes_ponto_nominal: dict
    tolerancias: dict
    operacao_paralelo: bool
    shutoff_min_paralelo_m: Decimal | None
    criterios_adicionais: dict
    resultados: list[ResultRow]
```

Notes:
- `Decimal` (not `float`) preserves the notebook's decimal-comma input ("0,567"); a custom validator splits on `,` → `.` before parsing.
- `schema_version` enables non-breaking evolution.

### 5.2 Functions (`pump/io/json_io.py`)

```python
def load_input(path_or_str_or_dict) -> PumpInputDocument: ...
def dump_input(doc: PumpInputDocument, path, *, indent=2) -> Path: ...
def load_result(path) -> PumpResultDocument: ...
def dump_result(doc: PumpResultDocument, path, *, indent=2) -> Path: ...

def input_to_models(doc: PumpInputDocument) -> tuple[Fluid, DesignPoint, list[TestPoint]]:
    """Convert the JSON document into typed library objects (with Pint Q_)."""
```

### 5.3 Legacy compatibility (`pump/io/legacy.py`)

The notebook's `_apply_form_data` already handles a legacy key (`dens_rated` instead of `dens_rel`, divides by 1000). Mirror that here so the on-disk JSONs in `examples/` keep loading after the refactor. Implement as a pre-validation hook.

### 5.4 UI hooks

Both UI modes wire to the same two functions:

- **Importar dados** (`<input>` upload → POST `/api/input/parse`) → renders the form pre-populated.
- **Exportar dados** (form snapshot → POST `/api/input/dump`) → triggers a browser download / native file save.
- **Salvar dados** on the results panel → `dump_result()` to the user-chosen path.
- **Exportar Word** → calls `ReportGenerator.generate(result_doc, language=ui_locale)`.

---

## 6 · UI modes — both supported

Per the user's choice: ship the classic notebook-faithful layout AND a modernized wizard, behind a toggle.

### 6.1 Mode A — `classic`

A single page, top-to-bottom regions identical to §1.1, rendered with NiceGUI primitives:

```
ui.radio(['bar', 'kgf/cm²'])                       # pressure unit
ui.select(STANDARDS)                                # applicable standard
ui.checkbox('Bomba operando em paralelo')           # parallel
with ui.expansion('Ponto Nominal (Folha de Dados)', value=True):
    ui.grid(columns=4)                              # 8 fields, 2-column
with ui.expansion('Pontos de Ensaio', value=True):
    ui.aggrid({...})                                # editable, head auto-calc
ui.button('Importar dados', on_click=...)
ui.button('Exportar dados', on_click=...)
ui.button('Calcular e gerar gráficos', on_click=...)
```

When `Calcular` is clicked → opens a `ui.dialog` (full-screen) with a `ui.splitter`: left = matplotlib figure, right = results table (mirrors §1.2 / §1.3).

### 6.2 Mode B — `wizard`

A 4-step stepper, same data backing:

1. **Setup** — pressure unit · standard · parallel operation.
2. **Rated point** — 8 fields with inline validation (e.g. `0 < dens_rel < 2`).
3. **Test points** — editable AG-grid table; sticky toolbar to add/remove rows and auto-fill head.
4. **Curves & report** — combined plots + acceptance table + download buttons.

Switching modes preserves form state (it's the same pydantic document under the hood).

### 6.3 Where the toggle lives

A simple `ui.toggle(['classic', 'wizard'])` in the header, persisted to `localStorage` (web) or `~/.pump-ui.json` (native).

---

## 7 · Implementation roadmap

Phases are deliberately decoupled so each ends in shippable, demonstrable state.

### Phase 0 — Library prerequisites (no UI, ~3 days)

- [ ] Add `pump/corrections.py` with `affinity_correct(point, rated)`, `viscosity_correction_factors`, `water_density_kgm3`, `pressure_to_head` (extracted from notebook).
- [ ] Add `CubicSplineFitter` to `pump/performance_curve.py` (wrap `scipy.interpolate.CubicSpline(..., bc_type='natural')`).
- [ ] Extend `PerformanceChecker` with `standard: Literal["API610", "ASME B73", "ISO 5199"]` and parallel-operation criterion.
- [ ] Fix or delete `Point.outlet_pressure` ([pump/point.py](pump/point.py)).
- [ ] Unit tests against the notebook's existing fixtures in [examples/](examples/) (Teste B-432201C, B-432301D, 52-P-11AB).

Exit criterion: a 30-line `pump.cli` script reproduces the notebook's printed table byte-for-byte from `Teste B-432201C 28abr26 (1).json`.

### Phase 1 — JSON I/O layer (~1 day)

- [ ] `pump/io/schemas.py` + `pump/io/json_io.py` + `pump/io/legacy.py`.
- [ ] Round-trip property test: `dump_input(load_input(x)) == x` for every JSON in `examples/`.
- [ ] Snapshot test: result JSON of fixture matches the existing `examples/c:\Users\U3BN\pump_api611_resultado.json`.

### Phase 2 — UI skeleton (NiceGUI scaffold) (~2 days)

- [ ] `pump/app/server.py` factory + `python -m pump.app --host/--port/--native`.
- [ ] Header with mode toggle, locale switch (`en`/`pt`).
- [ ] `pages/classic.py` static layout (no logic yet), `pages/wizard.py` empty shell.

### Phase 3 — Classic mode features (~4 days)

- [ ] Rated form + test-points editable table (live head-from-pressure).
- [ ] `Calcular` button → calls library → renders plots dialog + results panel.
- [ ] `Importar` / `Exportar` (input JSON) wired to `json_io`.
- [ ] `Salvar dados` (result JSON) + `Exportar Word` (via `ReportGenerator`).

### Phase 4 — Wizard mode (~2 days)

- [ ] 4-step stepper sharing the same state object.
- [ ] Per-step validation messages.

### Phase 5 — Packaging (~2 days)

- [ ] `build/pump-desktop.spec` PyInstaller config (collect `pump.templates`, `pump.utilities.locales`, matplotlib backends).
- [ ] GitHub Actions matrix (`windows-latest` / `macos-latest` / `ubuntu-latest`) producing artefacts on tag.
- [ ] `build/Dockerfile` for the web deployment.
- [ ] Smoke test: run the produced `.exe` on a clean Windows VM, import `Teste B-432201C 28abr26 (1).json`, calculate, export Word — verify file opens.

### Phase 6 — Polish (ongoing)

- [ ] Playwright smoke tests against the running NiceGUI server.
- [ ] Translate any remaining strings into `pump/utilities/locales/en/LC_MESSAGES/messages.po` and compile.
- [ ] Replace the broken `pyproject.toml` duplicate in [tests/pyproject.toml](tests/pyproject.toml) (unrelated cleanup flagged in [CLAUDE.md](CLAUDE.md)).

---

## 8 · Open questions to resolve before phase 1

1. **Decimal-comma policy.** Keep accepting `"0,567"` on input (Brazilian locale) but always **emit** dotted decimals on export? Or honour the active UI locale on emit too?
2. **`Point` class fate.** Delete (and update [CLAUDE.md](CLAUDE.md)) or fix? It's currently dead code.
3. **Acceptance checklist content.** The notebook hardcodes noise/seal-leak and API 610 vibration criteria in Portuguese — move these to the `.po` files or to a separate YAML config so users can extend them?
4. **`H_shutoff` source.** Today the user enters it on the rated form. Should the UI also read it from the curve fit (the smallest-Q point or `poly(0)`) and compare both? The notebook does both — make it explicit.
5. **Multi-tag reporting.** `ReportGenerator` already supports a dict of tags → tests (multi-pump report). Should the UI expose batch-mode (run several pumps, produce one PDF) or stay single-pump per session?

---

## 9 · TL;DR

- Promote the notebook's spline + multi-standard tolerance logic into the `pump` library so the math lives in one place, with units.
- Add `pump/io/` (pydantic schemas, round-trippable JSON, legacy-compat shim).
- Build the UI with **NiceGUI** — one Python codebase served as a web app and packaged with PyInstaller as a desktop executable that opens in a system webview.
- Ship both a **classic** (notebook-faithful) layout and a **wizard** (4-step) layout behind a single toggle.
- Reuse the existing `ReportGenerator` (python-docx + gettext) for Word output; existing matplotlib charts embed directly into NiceGUI via `ui.pyplot()`.
