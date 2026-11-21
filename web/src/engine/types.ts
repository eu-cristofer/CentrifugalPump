// Mirrors the module docstring of pumpflow/webapi.py.

export interface Quantity {
  value: number;
  unit: string;
}

export interface Port {
  name: string;
  type: string;
}

export interface CatalogEntry {
  kind: string;
  title: string;
  glyph: string;
  group: string;
  inputs: Array<Port & { multi: boolean }>;
  outputs: Port[];
  has_web_form: boolean;
}

export type NodeState = "idle" | "ok" | "invalid" | "error" | "reject";
export type Tone = "ok" | "fail" | "warn";
export type Badge = [text: string, tone: Tone];
export type RowVerdict = "pass" | "fail" | "info" | "n/e";

export interface ComplianceRow {
  name: string;
  actual: number | null;
  predicted: number | null;
  min: number | null;
  max: number | null;
  deviation: number | null;
  tol: number | null;
  verdict: RowVerdict;
  note: string;
  extrapolated: boolean;
  verified: boolean;
  /** the nine table cells as text, formatted in Python like the desktop */
  cells: string[];
}

export interface ComplianceView {
  default_tolerances?: Record<string, number | null>;
  pump_tag: string;
  verdict_text: string;
  verdict_label: string;
  overall_pass: boolean;
  criteria_label: string;
  overridden: boolean;
  override_reason: string;
  unverified: string[];
  not_evaluated: string[];
  parallel_ok: boolean | null;
  tolerances: Record<string, unknown>;
  rows: ComplianceRow[];
}

/** Per-kind display data; `{}` for kinds without a view, `{error}` if a view raised. */
export type NodeView = Record<string, unknown> | { error: string };

export interface NodeResult {
  kind: string;
  state: NodeState;
  status: string;
  badge: Badge | null;
  notes: string[];
  view: NodeView;
}

export interface EvaluateResult {
  nodes: Record<string, NodeResult>;
  /** ids of the nodes in state "error" */
  errors: string[];
}

/** A `.pumpflow` document (schema v1 or v2); opaque to the browser. */
export type PumpflowDoc = Record<string, unknown>;

export type ExportFormat = "docx" | "html" | "summary_xlsx";

export interface ExportResult {
  filename: string;
  mime: string;
  base64: string;
}

export type Settings = Record<string, unknown>;

/** `rated_point` view (after evaluate): the wired Fluid nodes and the active override. */
export interface RatedPointView {
  fluids: string[];
  choice: string;
  override: {
    name: string;
    density_rel: number;
    density_kgm3: number | null;
    viscosity_cst: number | null;
  } | null;
}

/** `fluid` view (after evaluate; `{}` while the node is invalid). */
export interface FluidView {
  name: string;
  source: string;
  density_kgm3: number | null;
  density_rel: number | null;
  viscosity_cst: number | null;
  viscosity_cp: number | null;
}

export type TestRowData = Record<string, number | null>;

/** `test_points` view (after evaluate). */
export interface TestPointsView {
  pump_tag: string;
  n_rows: number;
  head_unit: string;
  eff_unit: string;
  rows: Array<{
    head: number | null;
    eff: number | null;
    components: Record<string, number | null> | null;
  }>;
  fluids: string[];
  choice: string;
  has_shutoff: boolean;
  test_fluid: { name: string; density_kgm3: number | null } | null;
  pump_type: string;
  vib_label: string;
  vib_columns: Array<{ key: string; title: string; tooltip: string }>;
}

/** Result of `parse_paste`. */
export interface PasteResult {
  rows: TestRowData[];
  columns: Record<string, string>;
  pressure_ref: string;
  vibration: boolean;
  warnings: string[];
}

export interface BeforeAfterRow {
  q: number | null;
  head: number | null;
  power: number | null;
  eff: number | null;
}

/** `correction` view: the first four keys are always present, the rest after a result. */
export interface CorrectionView {
  fluids: string[];
  choice: string;
  has_rated: boolean;
  has_fluid: boolean;
  viscous_text?: string;
  banner?: { text: string; level: "info" | "warn" | "error" };
  before_after?: Array<{ measured: BeforeAfterRow; corrected: BeforeAfterRow }>;
}

/** One of the points / polynomial / spline blocks of a fit (canonical units: m3/h, m, kW, %). */
export interface SeriesBlock {
  q: number[];
  head: number[];
  power: number[] | null;
  eff: number[] | null;
}

/** The series part of a `curve_fit` view (and `performance_plot.fit`). */
export interface FitSeries {
  pump_tag?: string;
  degree?: number;
  points: SeriesBlock;
  poly: SeriesBlock;
  spline: SeriesBlock | null;
}

/** `curve_fit` view: the text parts and, once fitted, the series of the preview chart. */
export type CurveFitView = Partial<FitSeries> & {
  r2?: Record<string, number | null>;
  r2_text?: string;
  coeff_text?: string;
};

/** NPSHr test points and fitted curve (m3/h, m). */
export interface NpshSeries {
  points: { q: number[]; npshr: number[] } | null;
  curve: { q: number[]; npshr: number[] } | null;
}

export interface PlotRated {
  q: number;
  head: number | null;
  power: number | null;
  head_fit: number | null;
  power_fit: number | null;
  eff_fit: number | null;
  in_range: boolean;
}

export interface PlotShow {
  poly: boolean;
  spline: boolean;
  points: boolean;
}

/** `performance_plot` view (after evaluate; `{}` while no model is wired). */
export interface PerformancePlotView {
  pump_tag: string;
  fit: FitSeries;
  rated: PlotRated | null;
  npsh: (NpshSeries & { npsha: number | null; npshr_quoted: number | null }) | null;
  show: PlotShow;
}

/** `npsh` view (after evaluate; `{}` while the node is invalid). */
export type NpshView = Partial<NpshSeries> & {
  pump_tag: string;
  mode: string;
  status: "pass" | "fail" | "info";
  verdict: string;
  verified: boolean;
  criteria_label: string;
  npsha: number | null;
  npshr: number | null;
  margin: number | null;
  ratio: number | null;
  npshr_quoted: number | null;
  quoted_ok: boolean | null;
  min_ratio: number | null;
  min_margin: number | null;
  npshr_tol_plus: number | null;
  rated_q: number | null;
};

export interface MrtCheckRow {
  name: string;
  role: string;
  unit: string;
  min: Quantity | null;
  max: Quantity | null;
  last: Quantity | null;
  limit: Quantity | null;
  stabilisation: {
    change: Quantity | null;
    allowed: Quantity | null;
    window: Quantity | null;
    ok: boolean | null;
  } | null;
  status: string;
}

/** `mechanical_run_check` view (after evaluate; `{}` while no log is wired). */
export interface MrtCheckView {
  pump_tag: string;
  verdict: string;
  verdict_label: string;
  inputs_text: string;
  passed: boolean;
  fully_assessed: boolean;
  verified: boolean;
  source: string;
  criteria_label: string;
  duration: Quantity | null;
  min_duration: Quantity | null;
  duration_status: string;
  rows: MrtCheckRow[];
}

/** One channel of an MRT Log (runtime settings shape). */
export interface MrtColumn {
  name: string;
  dimension: string;
  unit: string;
  role: string;
}

/** One reading of an MRT Log. */
export interface MrtRow {
  time: string;
  values: Record<string, number | null>;
}

/** `mrt_options()`: channel roles, channel dimensions, dimension of each role's limits. */
export interface MrtOptions {
  roles: string[];
  dimensions: string[];
  role_dimensions: Record<string, string>;
}

export interface WaterProperties {
  density: number;
  kinematic_cst: number;
  dynamic_cp: number;
}

/** Arguments and result of each function the worker may call. */
export interface ApiFns {
  catalog: { args: []; result: CatalogEntry[] };
  evaluate: { args: [doc: PumpflowDoc]; result: EvaluateResult };
  default_settings: { args: [kind: string]; result: Record<string, unknown> };
  export_report: {
    args: [doc: PumpflowDoc, fmt: ExportFormat, lang: string | null];
    result: ExportResult;
  };
  decode_settings: { args: [kind: string, encoded: Settings]; result: Settings };
  encode_settings: { args: [kind: string, runtime: Settings]; result: Settings };
  unit_options: { args: [dimension: string]; result: Array<[label: string, pint: string]> };
  convert: {
    args: [
      value: number,
      from: string,
      to: string,
      dimension: string,
      densRel: number | null,
    ];
    result: number | null;
  };
  explain: { args: [key: string]; result: string };
  standards: { args: []; result: Array<[key: string, label: string]> };
  clients: { args: []; result: Array<[key: string, label: string]> };
  standard_label: { args: [key: string, client: string | null]; result: string };
  water_density: { args: [tempC: number]; result: number };
  water_properties: { args: [tempC: number]; result: WaterProperties };
  pump_types: { args: []; result: Array<[code: string, description: string]> };
  pump_type_hint: { args: [code: string]; result: string };
  atmosphere: { args: [unit: string]; result: number };
  parse_paste: {
    args: [text: string, columns: Record<string, string>, pressureRef: string];
    result: PasteResult;
  };
  next_time: { args: [rows: Array<{ time?: string }>]; result: string };
  mrt_options: { args: []; result: MrtOptions };
  parse_mrt_paste: { args: [text: string, columns: MrtColumn[]]; result: MrtRow[] };
}
export type FnName = keyof ApiFns;

export interface Progress {
  stage: string;
  loaded: number;
  total: number;
}

export interface CallMessage {
  id: number;
  fn: FnName;
  args: unknown[];
}

export type WorkerIn = CallMessage;

export type WorkerOut =
  | ({ type: "progress" } & Progress)
  | { type: "ready"; version: string }
  | { type: "fatal"; error: string }
  | { id: number; ok: true; result: unknown }
  | { id: number; ok: false; error: string };
