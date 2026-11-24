import { useEffect, useState } from "react";
import type { ComplianceView } from "../engine/types";
import { useEngine } from "./engineContext";
import { Banner, Checkbox, Divider, NumberField, Row, TextField } from "./fields";
import type { FormProps } from "./forms.types";
import { getStr } from "./settings";
import { useNodeForm } from "./useNodeForm";

const HEADERS = [
  "Parameter",
  "Actual",
  "Predicted",
  "Min",
  "Max",
  "Deviation",
  "Tol.",
  "Verdict",
  "Note",
];
const TOL_MAX_PCT = 50;
const EMPTY_REASON_PLACEHOLDER = "e.g. purchaser agreement, ref. letter / MoM no.";

type Tolerances = Record<string, number | null | undefined>;

const VERDICT_TONE: Record<string, string> = {
  APPROVED: "ok",
  REJECTED: "error",
  "NOT FULLY ASSESSED": "warn",
};

function asTolerances(v: unknown): Tolerances {
  if (!v || typeof v !== "object") return {};
  const out: Tolerances = {};
  for (const [k, x] of Object.entries(v as Record<string, unknown>)) {
    if (x === null || (typeof x === "number" && Number.isFinite(x))) out[k] = x;
  }
  return out;
}

/** API 610 Compliance Check — mirrors pumpflow/nodes/compliance.py (UI_SPEC §5.6). */
export default function ComplianceForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const view = (result?.view ?? {}) as Partial<ComplianceView>;
  const [open, setOpen] = useState<boolean | null>(null);
  const storedReason = s ? getStr(s, "override_reason") : "";
  // what is typed in Reason (null: show the stored one)
  const [typed, setTyped] = useState<string | null>(null);
  const [effDraft, setEffDraft] = useState<number | null>(null);
  useEffect(() => {
    // an outside change (undo) replaces what is typed; own typing is left alone
    setTyped((r) => (r !== null && r.trim() !== storedReason ? null : r));
  }, [storedReason]);
  const reason = typed ?? storedReason;
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const defaults = asTolerances(view.default_tolerances);
  const stored = asTolerances(s.tolerances);
  const cur: Tolerances = { ...defaults, ...stored };
  const hasResult = view.rows !== undefined;
  const overridden = view.overridden ?? false;
  const expanded = open ?? overridden;
  const effGuaranteed = cur.efficiency !== null && cur.efficiency !== undefined;
  const effShown = effGuaranteed ? (cur.efficiency as number) * 100 : (effDraft ?? 0);

  const writeTol = (patch: Tolerances) => {
    const next: Tolerances = { ...cur, ...patch };
    for (const k of Object.keys(next)) if (next[k] === undefined) delete next[k];
    update({ tolerances: next });
  };
  const pctField = (key: string, label: string) => {
    const v = cur[key];
    return (
      <Row label={label} suffix="%">
        <NumberField
          value={typeof v === "number" ? v * 100 : null}
          onChange={(p) => {
            if (p !== null && p >= 0 && p <= TOL_MAX_PCT) writeTol({ [key]: p / 100 });
          }}
        />
      </Row>
    );
  };

  const reset = () => {
    setTyped(null);
    setEffDraft(null);
    update({ tolerances: {}, override_reason: undefined });
  };

  const label = view.verdict_label ?? "";
  const tone = hasResult ? (VERDICT_TONE[label] ?? "error") : "idle";

  return (
    <div className="form-body">
      <div className={`verdict-banner verdict-${tone}`} role="status">
        {hasResult ? `${view.verdict_text}   ·   ${view.pump_tag}` : "—  awaiting inputs"}
      </div>
      {hasResult && view.criteria_label && <div>{`Criteria: ${view.criteria_label}`}</div>}
      {hasResult && (view.unverified?.length ?? 0) > 0 && (
        <p className="v-warn">
          {`⚠ Unverified against the standard text: ${(view.unverified ?? []).join(", ")}`}
        </p>
      )}
      {hasResult && view.parallel_ok !== null && view.parallel_ok !== undefined && (
        <div>
          {`Parallel operation: shut-off head rise ${view.parallel_ok ? "OK ✓" : "NOT MET ✗"}`}
        </div>
      )}
      {hasResult && overridden && (
        <Banner kind="warn">
          ⚠ Tolerances overridden — differ from the acceptance-criteria defaults.
        </Banner>
      )}
      {hasResult && (
        <div className="grid-wrap">
          <table className="grid" aria-label="Compliance parameters">
            <thead>
              <tr>
                {HEADERS.map((h, i) => (
                  <th key={h} className={i === 0 || i === 8 ? "grid-text" : undefined}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(view.rows ?? []).map((r) => (
                <tr key={r.name}>
                  {r.cells.map((c, i) => (
                    <td
                      key={i}
                      className={
                        i === 0 || i === 8
                          ? i === 8 && c
                            ? "grid-text note-warn"
                            : "grid-text"
                          : i === 7
                            ? `v-${r.verdict === "n/e" ? "warn" : r.verdict}`
                            : undefined
                      }
                    >
                      {c}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {error && <Banner kind="error">{error}</Banner>}
      {result?.state === "invalid" && <Banner kind="error">{result.status}</Banner>}
      <Divider />

      <button
        type="button"
        className="section-toggle"
        aria-expanded={expanded}
        onClick={() => setOpen(!expanded)}
      >
        <span aria-hidden="true">{expanded ? "▾" : "▸"}</span>
        Override acceptance criteria…
      </button>
      {expanded && (
        <div className="form-body">
          <Banner kind="warn">
            Changing a tolerance changes the verdict. The report states every overridden tolerance
            next to the criteria default, with the reason below.
          </Banner>
          {pctField("head", "Head")}
          {pctField("shutoff", "Shut-off head")}
          {pctField("power", "Power")}
          <Row label="">
            <Checkbox
              checked={effGuaranteed}
              label="Efficiency is guaranteed (purchaser-specified tolerance)"
              onChange={(v) => writeTol({ efficiency: v ? effShown / 100 : null })}
            />
          </Row>
          <Row label="Efficiency" suffix="%" disabled={!effGuaranteed}>
            <NumberField
              value={effShown}
              disabled={!effGuaranteed}
              onChange={(p) => {
                if (p !== null && p >= 0 && p <= TOL_MAX_PCT) {
                  setEffDraft(p);
                  writeTol({ efficiency: p / 100 });
                }
              }}
            />
          </Row>
          <Row label="Reason">
            <TextField
              value={reason}
              placeholder={EMPTY_REASON_PLACEHOLDER}
              onChange={(v) => {
                setTyped(v);
                update({ override_reason: v.trim() === "" ? undefined : v.trim() });
              }}
            />
          </Row>
          <Row label="">
            <button type="button" className="tool-button" onClick={reset}>
              Reset to the acceptance criteria
            </button>
          </Row>
        </div>
      )}
    </div>
  );
}
