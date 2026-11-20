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
}

export interface ComplianceView {
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

/** Arguments and result of each function the worker may call. */
export interface ApiFns {
  catalog: { args: []; result: CatalogEntry[] };
  evaluate: { args: [doc: PumpflowDoc]; result: EvaluateResult };
  default_settings: { args: [kind: string]; result: Record<string, unknown> };
  export_report: {
    args: [doc: PumpflowDoc, fmt: ExportFormat, lang: string | null];
    result: ExportResult;
  };
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
