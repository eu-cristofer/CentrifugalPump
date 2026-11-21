import { useEffect, useState } from "react";
import type { ExportFormat, PumpflowDoc, ReportExportView, Settings } from "../engine/types";
import { docNodes } from "../project/model";
import { downloadFile, printReport } from "./download";
import { useEngine } from "./engineContext";
import {
  Banner,
  Checkbox,
  Divider,
  Row,
  Section,
  Select,
  TextField,
  UnitField,
} from "./fields";
import type { FormProps } from "./forms.types";
import { getBool, getNumOrNull, getStr } from "./settings";
import { useNodeForm } from "./useNodeForm";
import "./reportExport.css";

const LANGUAGES: Array<[string, string]> = [
  ["English (EN)", "en"],
  ["Português (PT-BR)", "pt"],
];

const COVER_FIELDS: Array<[key: string, label: string, placeholder: string]> = [
  ["project", "Project", "project / contract"],
  ["client", "Client", "client"],
  ["location", "Location", "test location"],
  ["test_date", "Test date", "e.g. 2026-11-15"],
  ["revision", "Revision", "e.g. R0"],
];

/** The optional test data summary fields (pumpflow/binding/summary.py SUMMARY_FIELDS). */
const SUMMARY_FIELDS: Array<[key: string, label: string, placeholder: string]> = [
  ["purchaser", "Purchaser", "defaults to the client"],
  ["po_number", "Purchase order no.", ""],
  ["item_number", "Item no.", "defaults to the service TAG"],
  ["curve_number", "Curve no.", ""],
  ["stages", "No. of stages", "e.g. 1"],
  ["impeller_pattern", "Impeller pattern no.", ""],
  ["vanes", "No. of vanes", ""],
  ["volute_pattern", "Volute/diffuser pattern no.", ""],
  ["blade_tip_clearance", "Blade tip clearance (%)", ""],
];

type Pair = [key: string, value: string];

/** Rows that reach the settings: a non-empty key, and (when `unique`) the last of equal keys. */
function committed(rows: Pair[], unique: boolean): Pair[] {
  const kept = rows.filter(([k]) => k.trim() !== "");
  if (!unique) return kept;
  const last = new Map<string, string>();
  for (const [k, v] of kept) last.set(k, v);
  return [...last.entries()];
}

/**
 * Editable key/value rows (add and remove).  Rows with an empty key stay in the
 * editor until named; an outside change (undo / redo) replaces the rows.
 */
function PairTable({
  label,
  keyHeader,
  valueHeader,
  value,
  unique,
  disabled,
  addText,
  onChange,
}: {
  label: string;
  keyHeader: string;
  valueHeader: string;
  value: Pair[];
  unique: boolean;
  disabled?: boolean;
  addText: string;
  onChange: (rows: Pair[]) => void;
}) {
  const [rows, setRows] = useState<Pair[]>(value);
  const valueKey = JSON.stringify(value);
  useEffect(() => {
    setRows((cur) =>
      JSON.stringify(committed(cur, unique)) === valueKey
        ? cur
        : (JSON.parse(valueKey) as Pair[]),
    );
  }, [valueKey, unique]);

  const set = (next: Pair[]) => {
    setRows(next);
    onChange(committed(next, unique));
  };
  const edit = (i: number, col: 0 | 1, text: string) =>
    set(rows.map((r, j): Pair => (j === i ? (col === 0 ? [text, r[1]] : [r[0], text]) : r)));

  return (
    <div className="pair-table" role="group" aria-label={label}>
      {rows.map(([k, v], i) => (
        <div className="pair-row" key={i}>
          <input
            className="field"
            type="text"
            value={k}
            disabled={disabled}
            placeholder={keyHeader}
            aria-label={`${label} ${keyHeader.toLowerCase()} ${i + 1}`}
            onChange={(e) => edit(i, 0, e.target.value)}
          />
          <input
            className="field"
            type="text"
            value={v}
            disabled={disabled}
            placeholder={valueHeader}
            aria-label={`${label} ${valueHeader.toLowerCase()} ${i + 1}`}
            onChange={(e) => edit(i, 1, e.target.value)}
          />
          <button
            type="button"
            className="pair-remove"
            disabled={disabled}
            aria-label={`Remove ${label.toLowerCase()} row ${i + 1}`}
            onClick={() => set(rows.filter((_, j) => j !== i))}
          >
            ×
          </button>
        </div>
      ))}
      <button
        type="button"
        className="pair-add"
        disabled={disabled}
        onClick={() => set([...rows, ["", ""]])}
      >
        {addText}
      </button>
    </div>
  );
}

function asView(view: unknown): ReportExportView | null {
  const v = view as Partial<ReportExportView> | undefined;
  return v && Array.isArray(v.pumps) ? (v as ReportExportView) : null;
}

/** `doc` with the settings of node `nodeId` replaced (what the export sees). */
function withSettings(doc: PumpflowDoc, nodeId: string, settings: Settings): PumpflowDoc {
  return {
    ...doc,
    nodes: docNodes(doc).map((n) => (n.id === nodeId ? { ...n, settings } : n)),
  };
}

function toPairs(value: unknown): Pair[] {
  return value && typeof value === "object" && !Array.isArray(value)
    ? Object.entries(value as Record<string, unknown>).map(([k, v]): Pair => [k, String(v ?? "")])
    : [];
}

function signatoryPairs(value: unknown): Pair[] {
  if (!Array.isArray(value)) return [];
  return value.map((r): Pair => {
    const o = (r ?? {}) as Record<string, unknown>;
    return [String(o.role ?? ""), String(o.name ?? "")];
  });
}

/**
 * Report Export — mirrors pumpflow/nodes/report_export.py: cover page, signatories,
 * equipment, test data summary fields and the exports the browser can make (Word,
 * HTML, test data summary; print the HTML to PDF).  LaTeX / PDF is desktop only.
 * template_path and out_dir are desktop file paths and are not shown.
 */
export default function ReportExportForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const [busy, setBusy] = useState("");
  const [exportError, setExportError] = useState("");
  const [saved, setSaved] = useState("");
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const view = asView(result?.view);
  const reportable = !!view && view.pumps.some((p) => p.reportable);
  const language = getStr(s, "language", "en");
  const signaturesOn = getBool(s, "include_signatures", true);
  const ambientOn = getNumOrNull(s, "ambient_temp") !== null;

  const run = async (fmt: ExportFormat, print: boolean) => {
    // A window opened after an await is blocked as a pop-up, so open it in the click.
    let win: Window | null = null;
    if (print) {
      win = window.open("", "_blank");
      if (!win) {
        setExportError("The browser blocked the new tab. Allow pop-ups for this page and try again.");
        return;
      }
    }
    setBusy(print ? "print" : fmt);
    setExportError("");
    setSaved("");
    try {
      // the form's debounced edits may not be in `doc` yet: export what is on screen
      const encoded = await engine.encodeSettings("report_export", s);
      const file = await engine.exportReport(withSettings(doc, nodeId, encoded), fmt, language);
      if (win) {
        printReport(win, file);
      } else {
        downloadFile(file);
        setSaved(`Saved ${file.filename}`);
      }
    } catch (err) {
      win?.close();
      setExportError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
    }
  };

  const button = (text: string, fmt: ExportFormat, print = false, primary = false) => {
    const id = print ? "print" : fmt;
    return (
      <button
        type="button"
        className={`report-button${primary ? " report-button-primary" : ""}`}
        disabled={!reportable || busy !== ""}
        onClick={() => void run(fmt, print)}
      >
        {busy === id ? "Working…" : text}
      </button>
    );
  };

  return (
    <div className="form-body">
      <Section title="Connected pumps" />
      {view && view.pumps.length > 0 ? (
        <>
          <ul className="report-pumps" aria-label="Connected pumps">
            {view.pumps.map((p) => (
              <li className="report-pump" key={p.tag}>
                {p.tag} — {p.verdict_text ?? "no performance verdict"}
                <span className="report-pump-sections">
                  sections: {p.sections.length ? p.sections.join(" · ") : "none"}
                </span>
              </li>
            ))}
          </ul>
          <p className="report-muted">Overall verdict: {view.overall_verdict_text}</p>
        </>
      ) : (
        <Banner kind="info">
          {view && !view.has_rated
            ? "Connect the rated point and at least one fitted branch."
            : "No branches connected."}
        </Banner>
      )}
      <Divider />
      <Section title="Output" />
      <Row label="Language">
        <Select value={language} options={LANGUAGES} onChange={(v) => update({ language: v })} />
      </Row>
      <Row label="File name">
        <TextField
          value={getStr(s, "filename")}
          placeholder="Report"
          onChange={(v) => update({ filename: v })}
        />
      </Row>
      <Divider />
      <Section title="Cover page" />
      {COVER_FIELDS.map(([key, label, placeholder]) => (
        <Row key={key} label={label}>
          <TextField
            value={getStr(s, key)}
            placeholder={placeholder}
            onChange={(v) => update({ [key]: v })}
          />
        </Row>
      ))}
      <Section title="Signatories" />
      <Checkbox
        checked={signaturesOn}
        label="Include signature block in the report"
        // stored only when off, so older projects re-save unchanged
        onChange={(v) => update({ include_signatures: v ? undefined : false })}
      />
      <PairTable
        label="Signatory"
        keyHeader="Role"
        valueHeader="Name"
        value={signatoryPairs(s.signatories)}
        unique={false}
        disabled={!signaturesOn}
        addText="Add signatory"
        onChange={(rows) => update({ signatories: rows.map(([role, name]) => ({ role, name })) })}
      />
      <Divider />
      <Section title="Equipment description (service-level)" />
      <PairTable
        label="Equipment"
        keyHeader="Field"
        valueHeader="Value"
        value={toPairs(s.equipment)}
        unique
        addText="Add field"
        onChange={(rows) => update({ equipment: Object.fromEntries(rows) })}
      />
      <Divider />
      <Section title="Test data summary (API 610 Annex M / 8th ed. App. T)" />
      {SUMMARY_FIELDS.map(([key, label, placeholder]) => (
        <Row key={key} label={label}>
          <TextField
            value={getStr(s, key)}
            placeholder={placeholder}
            // stored only when filled
            onChange={(v) => update({ [key]: v.trim() ? v : undefined })}
          />
        </Row>
      ))}
      <Checkbox
        checked={ambientOn}
        label="Ambient temperature recorded"
        onChange={(on) =>
          update(
            on
              ? { ambient_temp: 25, ambient_temp_unit: getStr(s, "ambient_temp_unit", "°C") }
              : { ambient_temp: undefined, ambient_temp_unit: undefined },
          )
        }
      />
      <Row label="Ambient temperature" disabled={!ambientOn}>
        <UnitField
          dimension="temperature"
          value={getNumOrNull(s, "ambient_temp")}
          unit={getStr(s, "ambient_temp_unit", "°C")}
          disabled={!ambientOn}
          onChange={(v, u) => update({ ambient_temp: v ?? undefined, ambient_temp_unit: u })}
        />
      </Row>
      <Divider />
      <Section title="Export" />
      <div className="report-buttons">
        {button("Word (.docx)", "docx", false, true)}
        {button("HTML", "html")}
        {button("Test data summary (.xlsx)", "summary_xlsx")}
        {button("Print to PDF", "html", true)}
      </div>
      <p className="report-muted">
        Print to PDF opens the HTML report in a new tab; choose “Save as PDF” in the print dialog.
      </p>
      <p className="report-muted">
        LaTeX / PDF report: desktop app only (it needs a LaTeX installation).
      </p>
      {saved && <Banner kind="ok">{saved}</Banner>}
      {(exportError || error) && <Banner kind="error">{exportError || error}</Banner>}
    </div>
  );
}
