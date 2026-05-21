# UI plan — porting `pump_api610_performance 1.ipynb` into the `centrifugal-pump` library

> Source notebook: [examples/pump_api610_performance 1.ipynb](examples/pump_api610_performance%201.ipynb)
> Library entry points: [pump/point.py](pump/point.py), [pump/performance_curve.py](pump/performance_curve.py), [pump/utilities/unit_conversion.py](pump/utilities/unit_conversion.py), [pump/utilities/report.py](pump/utilities/report.py)
> Date: 2026-05-21
> Targets (committed): **iOS (iPad + iPhone, App Store)**, **Android (tablets + phones, Play Store)**, **desktop `.exe`** (Win/macOS/Linux), **shared web app**. The product is a **FAT records system** with the single-test calculator as its starting page.

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
| Mobile / WASM future | Pure-Python (numpy is the only C ext) → Pyodide-loadable on iOS if we ever want offline math in a WebView. | Trivially Pyodide-loadable. |

What's missing from the library and must be added:

1. **`CubicSplineFitter`** — natural cubic spline (notebook's `NaturalCubicSpline`) sitting next to `PerformanceFitter`. Wrap `scipy.interpolate.CubicSpline(..., bc_type="natural")` to avoid hand-rolling.
2. **`PerformanceChecker` multi-standard support** — extend `_norm_criteria` from the notebook (`API610` / `ASME B73` / `ISO 5199`) into `PerformanceChecker`. Today it only encodes API 610.
3. **Parallel-operation criterion** — `H_shutoff ≥ 1.10 × H_rated` switch.
4. **Pressure-derived head helper** — `TestPoint.from_pressures(p_suc, p_dis, unit, temp_c)` using the notebook's water-density polynomial.
5. **Viscosity correction factors** (README TODO) — `viscosity_correction_factors(nu_cst)` returning `(f_head, f_power, f_eff)`.
6. **Fix [`Point.outlet_pressure`](pump/point.py)** — currently a broken stub calling `quantity_factory()` with no args. Either delete `Point` or wire it correctly.

These are pure-library changes, no UI involved, and they unblock everything below.

---

## 3 · Recommended stack

Requirement set (confirmed): single-file desktop executable, shared web app, **iOS app on iPad/iPhone as priority**, Android app on tablets/phones, and persistent records system (history of FATs per pump TAG/plant/operator).

### 3.1 Stack options compared

| Stack | Web | Desktop exe | iOS / Android | Records / admin | Effort | Notes |
|---|---|---|---|---|---|---|
| **A. NiceGUI** | ✅ FastAPI under the hood | ✅ `ui.run(native=True)` + PyInstaller | ⚠️ PWA only; weak on iOS | ❌ build from scratch | Low | One-file Python UI; great for desktop+web prototyping. Mobile is post-hoc. |
| **B. FastAPI + React/Vue + PyWebView** | ✅ | ✅ PyWebView loads bundled JS | ✅ same JS → Capacitor / React Native | ⚠️ DIY | High | Native-feel SPA; two languages, two build pipelines. |
| **C. Streamlit** | ✅ | ⚠️ stlite/Electron | ❌ | ❌ | Lowest | Prototype-only. |
| **D. Dash / Plotly** | ✅ | ⚠️ PyWebView | ⚠️ web-responsive | ❌ | Low-Med | Great plots, weak forms, no records story. |
| **E. PySide6 (Qt) + FastAPI** | ✅ (sep. service) | ✅ | ⚠️ Qt for Mobile is rough | ❌ | High | Three UIs to maintain. |
| **F. Reflex** | ✅ | ⚠️ experimental | ⚠️ web-responsive | ❌ | Low | Younger ecosystem. |
| **G. BeeWare / Toga** | ⚠️ via web backend | ✅ Briefcase | ✅ true native `.ipa` / `.apk` via Briefcase | ❌ | High | Only Python-first path to true native mobile binaries. Limited widgets; no rich plot widget; small ecosystem; documenting tables/forms is painful. |
| **H. Django + HTMX + Alpine.js** (**recommended**) | ✅ best-in-class | ✅ PyWebView + PyInstaller wrap a bundled `localhost` Django server | ✅ Capacitor wrapping the same HTML → signed `.ipa` and `.apk`, App Store & Play Store distributable | ✅ **free Django admin + ORM** | Low-Med | Server-rendered HTML — the friendliest payload for tablets/phones, the easiest thing to Capacitor-wrap, the cheapest path to App Store builds, and the ORM + admin solve the records-system requirement on day one. |

### 3.2 Recommendation: **H — Django + HTMX + Alpine.js, wrapped with Capacitor (iOS/Android) and PyWebView (desktop)**

Justified against the four committed requirements:

1. **iOS priority for iPad/iPhone.** The cheapest, most reliable Python-backed path to a signed `.ipa` distributed via App Store / TestFlight is to wrap a server-rendered web bundle with Capacitor — and server-rendered HTML is exactly what Django produces. NiceGUI's Vue+Quasar payload is mobile-acceptable but heavier and gives nothing for app-store packaging beyond what we'd add ourselves. BeeWare/Toga is the only Python-first alternative that produces real `.ipa`, but its widget set has no rich plot widget and rebuilding the UX there is months of work.
2. **Records system.** Django ORM + admin give the records use case (`Pump` / `FATRun` / `TestPoint` / `Operator` / `Plant` models, with full CRUD, search, audit log, user auth) **for free**. NiceGUI/Reflex/Streamlit ship none of this; building it from scratch is weeks of work duplicating Django's solved problem.
3. **Desktop `.exe`.** Bundle a thin launcher: PyInstaller packages Python + Django + SQLite, the launcher boots Django on `127.0.0.1:<random>` in a background thread, then opens a PyWebView window pointed at it. Standard pattern (used by Mailpile, Calibre's content server UI, several pyqtdeploy/Django demos). More moving parts than NiceGUI's `ui.run(native=True)` but well-trodden.
4. **Shared web app.** Native fit — Django is what it was built for.

Why **HTMX + Alpine** (and not a SPA):
- The notebook's interactivity is small: live head-from-pressure, add/remove rows, swap in the plot panel when "Calcular" is clicked. HTMX (`hx-post`, `hx-swap`) covers the panel swaps; Alpine.js (`x-data`, `x-model`, computed bindings) covers the per-row recalculation. **No JS build step, no node_modules in the repo.**
- Tiny payload (HTMX ~14 kB, Alpine ~7 kB gzipped) → loads instantly on tablets over flaky Wi-Fi.
- Capacitor-wrapping a thin HTML payload is dramatically simpler than wrapping a Vue/React bundle.

Trade-offs accepted:
- Desktop `.exe` boot is ~1–2 s slower than NiceGUI's `native=True` (because Django + Gunicorn/uvicorn cold-start beats `ui.run`). Acceptable for a FAT tool used in long sessions.
- Matplotlib doesn't embed as a widget — we serve it as a PNG endpoint (`GET /api/v1/runs/{id}/chart.png?dpi=...`) **or** move plotting to Plotly via `plotly.js` (better on touch devices — pinch-zoom works). We'll do **both**: PNG for embedded reports, Plotly for the interactive view.
- The on-device offline story for iOS/Android Capacitor builds needs a decision (see §9.4): hosted backend vs. embedded SQLite + on-device math via Pyodide vs. plain-JS math port.

### 3.3 Final concrete stack

| Layer | Choice |
|---|---|
| Core math + units | `pump` package (Pint + numpy + scipy), extended per §2 |
| Persistence | SQLite (desktop bundle + dev), Postgres (server) — both via Django ORM |
| HTTP API (canonical contract) | **Django REST Framework** at `/api/v1/...`, OpenAPI-documented via `drf-spectacular`. Versioned so iOS/Android/desktop clients pin a schema. |
| Server-side UI | Django views + templates, `django-htmx` middleware, Alpine.js sprinkles. **Same templates** serve the web app and (via Capacitor) the iOS/Android apps. |
| Interactive plots | **Plotly.js** in the browser (touch-friendly), fed JSON from `/api/v1/runs/{id}/curves` |
| Static plots | matplotlib → PNG endpoint, embedded in `.docx` reports and exportable |
| Reports | `python-docx` via existing `pump.utilities.report.ReportGenerator`, kept unchanged |
| JSON I/O | `pydantic` v2 models for the **library boundary** (`pump.io`); DRF serializers for the **HTTP boundary**, both validating against the same canonical schema. |
| Admin / records | **Django admin** (CRUD, search, audit), `django-simple-history` for change-log per FAT run, `django-allauth` for SSO if/when needed. |
| Auth | Django sessions (web/desktop) + DRF token / OAuth2 (mobile). |
| Localization | Django i18n machinery, reusing the existing `pump/utilities/locales/{en,pt}` `.po` files. |
| Background work (Word export, big batch reports) | `django-q2` or `huey` with SQLite broker on desktop, Redis on server. |
| Packaging — desktop | `PyInstaller` one-file build: Django + uvicorn + PyWebView launcher → `.exe` / `.dmg` / `.AppImage`. CI matrix: `windows-latest`, `macos-latest`, `ubuntu-latest`. |
| Packaging — web | `Dockerfile` running `gunicorn pump.fat.wsgi` behind nginx, Postgres + Redis sidecars. |
| Packaging — iOS | `mobile/` Capacitor project, `npx cap add ios`, Xcode signing, TestFlight → App Store. Universal app (iPad + iPhone). |
| Packaging — Android | `mobile/` same project, `npx cap add android`, Android Studio signing, Play Console internal track → production. |
| Tests | `pytest-django` for engine + views, `playwright` against the running server for end-to-end, `XCUITest` / `Espresso` smoke on the wrapped mobile builds via Capacitor's e2e tooling. |

### 3.4 Why not the cheaper paths

- **NiceGUI** stays a great option for a *standalone calculator* but not for what the user actually asked for. iOS distribution via PWA is hostile (no proper offline, no file system access, limited push), and the records system would be a from-scratch build.
- **BeeWare/Toga** is the only other Python-first path to genuine native `.ipa`/`.apk`. It loses on widget richness (no good chart widget, hand-built tables), tooling maturity, and on the records system (no admin). For this product, server-rendered HTML wrapped in Capacitor is both easier and more flexible.
- **Pure React/Vue SPA + FastAPI** is a viable upgrade target if the UX ever outgrows HTMX (e.g. real-time multi-user dashboards). The Django REST API (§3.3) is the boundary that makes that migration possible without rewriting the engine.

---

## 4 · Target package layout

```
.
├── pump/                         # the calculation library (existing, extended)
│   ├── __init__.py
│   ├── point.py                  (fix Point.outlet_pressure)
│   ├── performance_curve.py      (+ CubicSplineFitter, multi-standard checker)
│   ├── corrections.py            (NEW — affinity, viscosity, water density)
│   ├── io/                       (NEW — canonical JSON schemas)
│   │   ├── schemas.py            (pydantic models for input/result JSON)
│   │   ├── json_io.py            (load_input / dump_input / load_result / dump_result)
│   │   └── legacy.py             (notebook-JSON compatibility shim)
│   ├── templates/                (existing .docx)
│   └── utilities/                (existing report.py, unit_conversion.py, locales/)
│
├── pumpfat/                      # NEW — Django project ("pump FAT")
│   ├── manage.py
│   ├── pumpfat/                  # project package
│   │   ├── settings/{base,dev,prod,desktop}.py
│   │   ├── urls.py
│   │   ├── wsgi.py / asgi.py
│   │   └── launcher.py           # PyWebView entrypoint for desktop bundle
│   ├── apps/
│   │   ├── catalog/              # Pump / Plant / Operator / Fluid models + admin
│   │   ├── runs/                 # FATRun, RatedPoint, TestPoint, Result models
│   │   ├── compute/              # thin Django-side bridge to pump.* engine
│   │   ├── api/                  # DRF viewsets + serializers + OpenAPI
│   │   └── ui/                   # views, templates, htmx fragments, Alpine
│   ├── templates/
│   │   ├── base.html             # navbar, locale switch, mode toggle
│   │   ├── runs/
│   │   │   ├── classic.html      # one-page notebook-faithful layout
│   │   │   ├── wizard.html       # 4-step stepper
│   │   │   ├── _points_table.html   # HTMX fragment
│   │   │   ├── _curves_panel.html
│   │   │   └── _results_panel.html
│   │   └── catalog/              # admin-adjacent dashboards
│   ├── static/
│   │   ├── js/
│   │   │   ├── htmx.min.js
│   │   │   ├── alpine.min.js
│   │   │   └── plotly.min.js
│   │   └── css/pumpfat.css
│   ├── locale/{en,pt}/LC_MESSAGES/ # symlinks to pump/utilities/locales/*
│   └── fixtures/                 # sample DB seeded from examples/*.json
│
├── mobile/                       # NEW — Capacitor project (iOS + Android shell)
│   ├── package.json
│   ├── capacitor.config.ts       # webDir, plugins (Filesystem, Share, Network)
│   ├── ios/                      # native shell (Xcode workspace)
│   ├── android/                  # native shell (Gradle)
│   └── www/                      # built static + service worker (or live URL)
│
├── build/
│   ├── desktop.spec              # PyInstaller spec for the launcher
│   ├── Dockerfile                # web image
│   └── ios-fastlane/             # CI signing + TestFlight upload
│
├── tests/
│   ├── unit/                     # pump.* engine
│   ├── api/                      # DRF endpoints
│   ├── ui/                       # playwright against running server
│   └── mobile/                   # Capacitor e2e
│
└── examples/                     # unchanged — used as test fixtures
```

---

## 5 · Data model and JSON I/O

### 5.1 Django models (`pumpfat/apps/runs/models.py`)

```python
class Plant(models.Model):
    name = models.CharField(max_length=120, unique=True)

class Pump(models.Model):
    tag        = models.CharField(max_length=60, unique=True)
    plant      = models.ForeignKey(Plant, on_delete=PROTECT, null=True)
    standard   = models.CharField(max_length=80, choices=STANDARDS)
    parallel_operation = models.BooleanField(default=False)

class RatedPoint(models.Model):
    pump        = models.OneToOneField(Pump, on_delete=CASCADE)
    q_m3h, head_m, n_rpm, power_kw = (models.DecimalField(...) for _ in range(4))
    dens_rel, visc_nom_cst, head_shutoff_m = ...

class FATRun(models.Model):
    pump        = models.ForeignKey(Pump, on_delete=PROTECT, related_name="runs")
    operator    = models.ForeignKey(User, on_delete=PROTECT)
    performed_at = models.DateTimeField(default=timezone.now)
    pressure_unit = models.CharField(choices=PRESSURE_UNITS)
    snapshot     = models.JSONField()   # canonical pydantic doc (audit-stable)
    result       = models.JSONField(null=True)  # populated after Calcular

class TestPointRecord(models.Model):
    run = models.ForeignKey(FATRun, related_name="points", on_delete=CASCADE)
    order = models.PositiveSmallIntegerField()
    q, p_suc, p_dis, temp_c, head, power, n_rpm = (models.DecimalField(...) ...)
```

`snapshot` is the load-bearing JSON — the same shape as the notebook on-disk format (§1.4). The relational rows mirror it for querying but the snapshot is the source of truth. `django-simple-history` tracks edits.

### 5.2 pydantic schemas (`pump/io/schemas.py`) — library boundary

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
    head: Decimal | None = None     # auto-computed from p_suc/p_dis if absent
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
    desvio:  Decimal | None
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
- `Decimal` (not `float`) preserves the notebook's decimal-comma input (`"0,567"`); a pre-validator splits on `,` → `.` before parsing.
- `schema_version` enables non-breaking evolution.

### 5.3 DRF serializers — HTTP boundary

DRF serializers wrap the pydantic models so the REST API validates payloads identically to the library, but uses Django's renderer/parser pipeline. A 30-line adapter (`pump/io/drf.py`) converts pydantic `ValidationError` → DRF `ValidationError`.

### 5.4 Library boundary functions (`pump/io/json_io.py`)

```python
def load_input(path_or_str_or_dict) -> PumpInputDocument: ...
def dump_input(doc: PumpInputDocument, path, *, indent=2) -> Path: ...
def load_result(path) -> PumpResultDocument: ...
def dump_result(doc: PumpResultDocument, path, *, indent=2) -> Path: ...

def input_to_models(doc: PumpInputDocument) -> tuple[Fluid, DesignPoint, list[TestPoint]]:
    """Convert the JSON document into typed library objects (with Pint Q_)."""
```

### 5.5 Legacy compatibility (`pump/io/legacy.py`)

The notebook's `_apply_form_data` already handles a legacy key (`dens_rated` → `dens_rel`, divided by 1000). Mirror that here so the on-disk JSONs in `examples/` keep loading after the refactor. Implement as a pydantic pre-validation hook.

### 5.6 REST endpoints (`pumpfat/apps/api/urls.py`)

| Verb | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/pumps/` | List/filter pumps (by TAG, plant, standard) |
| `POST` | `/api/v1/pumps/` | Create pump + rated point |
| `GET` | `/api/v1/pumps/{tag}/runs/` | History of FATs for this pump |
| `POST` | `/api/v1/runs/` | Submit a `PumpInputDocument` → returns 201 with `id` |
| `POST` | `/api/v1/runs/{id}/calculate/` | Trigger compute → returns `PumpResultDocument` |
| `GET` | `/api/v1/runs/{id}/chart.png` | Static matplotlib chart |
| `GET` | `/api/v1/runs/{id}/chart.json` | Plotly data for the touch-zoom chart |
| `GET` | `/api/v1/runs/{id}/report.docx` | Word report via `ReportGenerator` |
| `POST` | `/api/v1/runs/import/` | Upload a notebook-style JSON (also supports the legacy shape) |
| `GET` | `/api/v1/runs/{id}/export.json` | Download canonical JSON |

### 5.7 UI hooks

- **Importar dados** → `<input type="file">` → `POST /api/v1/runs/import/` → server returns 303 to the populated form.
- **Exportar dados** → link to `/api/v1/runs/{id}/export.json` (browser/Capacitor handle the save).
- **Salvar dados** (results) → button posts current state then redirects to `export.json`.
- **Exportar Word** → link to `/api/v1/runs/{id}/report.docx?locale=pt` (or `en`).

On Capacitor (iOS/Android) the `<a href>` downloads are intercepted by the `@capacitor/filesystem` plugin to write to the platform's Files / Documents app.

---

## 6 · UI modes — both supported

Per the earlier choice: ship the classic notebook-faithful layout AND a modernized wizard, behind a toggle. With Django, both modes are templates over the same `FATRun` and the same form state in `session["draft"]`.

### 6.1 Mode A — `classic`

Single page at `/runs/new/?mode=classic`, structure mirrors §1.1:

```html
<form hx-post="{% url 'runs:save_draft' %}" hx-trigger="change delay:300ms"
      x-data="ratedForm(initial)">

  {# Pressure unit / Standard / Parallel #}
  <fieldset>…radios, select, checkbox…</fieldset>

  {# Rated point — 8 fields, 2-col grid #}
  <fieldset>…inputs bound with x-model, validation via Alpine…</fieldset>

  {# Test points table — Alpine handles add/remove + live head calc #}
  <table>
    <template x-for="(p, idx) in points" :key="idx">
      <tr>
        <td><input x-model.number="p.q"></td>
        <td><input x-model.number="p.p_suc"></td>
        <td><input x-model.number="p.p_dis"></td>
        <td><input x-model.number="p.temp_c"></td>
        <td x-text="formatHead(p)"></td>   {# live head #}
        <td><input x-model.number="p.power"></td>
        <td><input x-model.number="p.n_rpm"></td>
      </tr>
    </template>
  </table>

  <button hx-post="{% url 'runs:calculate' draft.id %}"
          hx-target="#results" hx-swap="innerHTML">Calcular</button>
</form>

<section id="results"></section>   {# HTMX swaps in _curves_panel + _results_panel #}
```

`Calcular` returns an HTML fragment containing the Plotly `<div>` (touch-friendly, mobile-first), the 6-column results table, and a download bar (`Salvar dados`, `Exportar Word`).

### 6.2 Mode B — `wizard`

`/runs/new/?mode=wizard` renders the same form data through a 4-step stepper template, each step posting to the same `save_draft` endpoint:

1. **Setup** — pressure unit · standard · parallel operation.
2. **Rated point** — 8 fields with inline validation (`x-data` rules: `0 < dens_rel < 2`, etc.).
3. **Test points** — Alpine table; sticky toolbar to add/remove rows; auto-fill head.
4. **Curves & report** — Plotly chart + acceptance table + download buttons.

Both modes share `ratedForm()` Alpine component and the same `_curves_panel.html` / `_results_panel.html` partials.

### 6.3 Mode toggle

Header dropdown stored on the user profile (`User.preferences["ui_mode"]`) on the web, in `localStorage` on Capacitor builds. Switching modes preserves the draft (it's the same `FATRun` row).

### 6.4 Touch-friendly considerations baked in from the start

- Inputs sized ≥ 44 × 44 px (iOS HIG minimum touch target).
- `inputmode="decimal"` and `pattern="[0-9.,]*"` so iOS shows a number keypad with the comma key.
- Plotly with `responsive: true`, `displayModeBar: 'hover'` on desktop, `false` on touch (replaced by a custom segmented control: Q×H | Q×P | Q×η).
- Steppers and HTMX partial swaps keep scroll position via `hx-preserve` on long forms.

---

## 7 · Implementation roadmap

Phases are decoupled so each ends in a shippable artefact.

### Phase 0 — Library prerequisites (no UI, ~3 days)

- [ ] Add `pump/corrections.py` with `affinity_correct`, `viscosity_correction_factors`, `water_density_kgm3`, `pressure_to_head`.
- [ ] Add `CubicSplineFitter` to `pump/performance_curve.py` (wrap `scipy.interpolate.CubicSpline(..., bc_type='natural')`).
- [ ] Extend `PerformanceChecker` with `standard` enum (API610 / ASME B73 / ISO 5199) + parallel-operation criterion.
- [ ] Fix or delete `Point.outlet_pressure`.
- [ ] Unit tests against the notebook fixtures in [examples/](examples/) (Teste B-432201C, B-432301D, 52-P-11AB).

Exit criterion: a 30-line `pump.cli` script reproduces the notebook's printed table byte-for-byte from `Teste B-432201C 28abr26 (1).json`.

### Phase 1 — JSON I/O layer (~1 day)

- [ ] `pump/io/{schemas,json_io,legacy}.py`.
- [ ] Round-trip property test: `dump_input(load_input(x)) == x` for every JSON in `examples/`.
- [ ] Snapshot test: result JSON matches the existing `examples/c:\Users\U3BN\pump_api611_resultado.json` byte-for-byte.

### Phase 2 — Django scaffold + records data model (~3 days)

- [ ] `pumpfat/` project bootstrapped, settings split (`base`/`dev`/`prod`/`desktop`).
- [ ] Apps `catalog`, `runs`, `compute`, `api`, `ui` with initial migrations.
- [ ] Django admin registered for `Pump` / `Plant` / `FATRun` (CRUD + search + filter).
- [ ] `django-simple-history` enabled on `FATRun` and `RatedPoint`.
- [ ] Fixture loader: import every JSON under `examples/` as a seeded FATRun for dev.

### Phase 3 — REST API (`/api/v1`) + Plotly chart endpoint (~2 days)

- [ ] DRF viewsets + serializers + OpenAPI via `drf-spectacular`.
- [ ] `runs/{id}/calculate/`, `chart.png`, `chart.json`, `report.docx`, `export.json`, `import/`.
- [ ] `pytest-django` covers each endpoint with at least one happy-path and one validation failure.

### Phase 4 — Classic web UI (~4 days)

- [ ] Templates + Alpine `ratedForm()` + HTMX partials.
- [ ] Live head-from-pressure recalculation.
- [ ] Calcular → swap in Plotly chart + results panel.
- [ ] Importar / Exportar / Salvar dados / Exportar Word wired to API endpoints.

### Phase 5 — Wizard UI (~2 days)

- [ ] 4-step stepper template, per-step validation messages.
- [ ] Mode toggle in header, persisted per user / per device.

### Phase 6 — Desktop packaging (~3 days)

- [ ] `pumpfat/launcher.py` — boots Django on `127.0.0.1:<random>` via `uvicorn` thread, opens `PyWebView` window pointed at it.
- [ ] `build/desktop.spec` — PyInstaller spec collecting Django, templates, static, `pump.templates`, locale `.mo`, matplotlib backends, scipy.
- [ ] First-run migration onto a SQLite DB at `%APPDATA%/pumpfat/db.sqlite3` (or `~/Library/Application Support/pumpfat/` on macOS, `~/.local/share/pumpfat/` on Linux).
- [ ] GitHub Actions matrix (`windows-latest`, `macos-latest`, `ubuntu-latest`) producing artefacts on tag.
- [ ] Smoke test on a clean Windows VM: import `Teste B-432201C 28abr26 (1).json`, calculate, export Word.

### Phase 7 — Web deployment (~1 day)

- [ ] `build/Dockerfile` — gunicorn + Django + collected statics, Postgres + Redis sidecars in `docker-compose.yml`.
- [ ] Production settings: `ALLOWED_HOSTS`, `SECURE_*`, `CSRF_TRUSTED_ORIGINS`, S3 (or local) media backend.

### Phase 8 — iOS Capacitor build (~5 days) — **the priority mobile target**

- [ ] `mobile/` Capacitor project, `npx cap add ios`, points `server.url` at the hosted Django (or to a local bundled copy via `webDir`, see §9.4).
- [ ] Configure `@capacitor/filesystem` for JSON / Word downloads to Files app.
- [ ] iOS-specific tweaks: `viewport-fit=cover`, safe-area CSS, `inputmode="decimal"` everywhere, iPad split-view layout breakpoints.
- [ ] Native push (optional): `@capacitor/push-notifications` if test approvals need notifications.
- [ ] Sign with Apple Developer cert via `fastlane`, ship to TestFlight, internal testers in QA, then App Store review submission.

Exit criterion: app installs on an iPad and an iPhone via TestFlight, lets a test engineer log in, fill the rated form, add test points, calculate, and email the Word report — all on cellular.

### Phase 9 — Android Capacitor build (~2 days)

- [ ] `npx cap add android`, mirror the iOS configuration.
- [ ] Sign + upload to Google Play Console internal track → closed beta → production.

### Phase 10 — Polish (ongoing)

- [ ] Playwright smoke tests against the live Django server.
- [ ] Compile `pump/utilities/locales/en/LC_MESSAGES/messages.po`.
- [ ] Remove the broken `tests/pyproject.toml` duplicate flagged in [CLAUDE.md](CLAUDE.md).
- [ ] Add `django-allauth` SSO when the lab needs single-sign-on.
- [ ] Multi-tenancy / per-plant isolation if/when several plants share the deployment.

---

## 8 · Open questions to resolve before phase 1

1. **Decimal-comma policy.** Keep accepting `"0,567"` on input but always **emit** dotted decimals? Or honour the active locale on emit too?
2. **`Point` class fate.** Delete (and update [CLAUDE.md](CLAUDE.md)) or fix? It's currently dead code.
3. **Acceptance checklist content.** The notebook hardcodes noise/seal-leak + API 610 vibration criteria in Portuguese — move to `.po` files or to YAML config so users can extend them?
4. **`H_shutoff` source.** User enters it on the rated form; should the UI also derive it from the curve (`poly(0)`) and compare both? The notebook does both — make explicit.
5. **Multi-pump batch reports.** `ReportGenerator` already supports a dict of tags → tests. Expose batch-mode (one PDF for several pumps) or stay single-pump per session?
6. **Mobile offline scope.** See §9.4.

---

## 9 · Mobile packaging in depth

Capacitor is the load-bearing piece. The plan stays viable on iOS *and* Android because Capacitor wraps the **same** Django-rendered web bundle in a native shell that the App Store and Play Store accept.

### 9.1 Capacitor in one paragraph

Capacitor (by Ionic) takes a web app — HTML/CSS/JS — and produces a native iOS Xcode project and a native Android Gradle project, each containing a `WKWebView` (iOS) / `WebView` (Android) that loads either (a) a remote URL (`server.url` in `capacitor.config.ts`), or (b) a bundled `webDir/` of static files. The native shell can expose plugins (Filesystem, Camera, Share, Push, Network, Geolocation) callable from JS via a small bridge. The result is a normal `.ipa` and `.apk`, signed and shipped through the usual channels.

### 9.2 What this means concretely

| Concern | Plan |
|---|---|
| **App Store eligibility** | A Capacitor app is just a native app from the store's perspective — same review process as any Swift/Kotlin app. Apple Review item 4.7 explicitly permits webview-based apps that provide app-like functionality. |
| **Universal iOS app** | One target, two storyboards — iPhone (compact) and iPad (regular/regular). Both ship in one `.ipa`. |
| **Tablet layouts** | CSS media queries (`@media (min-width: 768px)`) split the wizard into side-by-side panes on iPad / Android tablets. |
| **Live HTML reload during dev** | `npx cap run ios --livereload` points the device's webview at the dev Django server on the LAN. |
| **Filesystem & sharing** | `@capacitor/filesystem` for saving the JSON / Word files into Files / Documents. `@capacitor/share` to AirDrop / e-mail them. |
| **Network state** | `@capacitor/network` shows an offline banner; failing API calls queue in `localStorage` and retry on reconnect. |
| **Authentication** | DRF token endpoint; Capacitor stores the token in `@capacitor/preferences` (Keychain on iOS, EncryptedSharedPreferences on Android). |

### 9.3 Build pipeline (CI)

GitHub Actions on tag push:

- Web bundle: `python manage.py collectstatic --noinput` → uploaded to S3 + served at `https://pumpfat.example.com`.
- iOS: `macos-latest` runner, Xcode 16+, `fastlane match` for certs, `npx cap sync ios && fastlane beta` → TestFlight.
- Android: `ubuntu-latest` runner, signed AAB, `fastlane supply` → Play Console internal track.
- Desktop: matrix as in Phase 6.

### 9.4 The offline question (the one real design decision)

For iPad/iPhone use during a FAT in a noisy plant, network reliability is the risk. Three options, picked per-build:

| Option | Capacitor `server.url` | On-device math | Bundle size | Offline? | Effort |
|---|---|---|---|---|---|
| **(i) Hosted, online-only** | `https://pumpfat.example.com` | None — Django does the math server-side | ~5 MB | ❌ requires connectivity | Lowest |
| **(ii) Hybrid — read-only offline** | Hosted | Cache last N runs in `localStorage` / `IndexedDB`; view-only when offline; "Calcular" disabled offline | ~10 MB | ⚠️ view yes, compute no | Low |
| **(iii) Full offline — Pyodide in webview** | `webDir/` (bundled HTML) | `pump` engine ported to **Pyodide** (Python in WASM, ships in the bundle) | ~40 MB extra | ✅ everything works offline; results sync to server on reconnect | High |

Recommendation: ship **(ii) Hybrid** in Phase 8 — fastest to market and matches how FAT engineers work today (test in shop, sync results back at end of day). Reserve **(iii) Pyodide** for a later phase if shop-floor connectivity proves too poor. The library being Pint+numpy+scipy *is* Pyodide-loadable today — numpy and scipy have first-class Pyodide builds, Pint is pure Python — so the door is left open without committing to it now.

### 9.5 Risks specific to mobile

- **Apple Review.** "Web wrapper" rejections (Guideline 4.2) are typical when the app is just a browser bookmark. We avoid this by (a) using native plugins (Filesystem, Share, Network, Preferences) so the app does things Safari can't, and (b) having a launch screen, splash, app icon, and offline behaviour. Plenty of Capacitor apps pass — this is not novel territory.
- **WebView differences.** iOS WKWebView and Android WebView are evergreen but subtly different. We need a Capacitor smoke test on both.
- **Plotly bundle size.** ~3 MB minified. Acceptable. If it bites, swap Plotly for `chart.js` or an SVG render at the small cost of less interactivity.
- **Font rendering of `²`, `³`, `η`, `≤`, `≥`.** Notebook UI uses these heavily. Ensure the bundled web font (or system stack) renders them on iOS and Android; otherwise fall back to `m^3/h`, `eta`, `<=`, `>=`.

---

## 10 · TL;DR

- Promote the notebook's spline + multi-standard tolerance logic into the `pump` library so the math lives in one place, with units.
- Add `pump/io/` (pydantic schemas, round-trippable JSON, legacy shim) as the **canonical library boundary**.
- Build a **Django** project (`pumpfat/`) with DRF as the **canonical HTTP boundary**, server-rendered templates with HTMX + Alpine.js for the UI, and Django admin / ORM for the FAT records system.
- Ship both a **classic** (notebook-faithful) layout and a **wizard** (4-step) layout behind a single toggle.
- Reuse the existing `ReportGenerator` (python-docx + gettext) for Word output; expose Plotly for interactive in-browser charts and matplotlib for embedded PNGs.
- Package for **iOS (iPad + iPhone)** and **Android (tablets + phones)** by wrapping the same Django bundle with **Capacitor**, distributed via App Store / Play Store. Desktop ships as a **PyInstaller** binary launching Django on `localhost` inside **PyWebView**. Web deploys via Docker.
- Mobile offline strategy starts as "hosted + cache" and leaves the door open for full-offline via Pyodide if shop-floor connectivity demands it.
