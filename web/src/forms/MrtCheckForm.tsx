import { useState } from "react";
import { localizeNumber } from "../decimal";
import type { MrtCheckRow, MrtCheckView, MrtRuleRow, Quantity } from "../engine/types";
import { useEngine } from "./engineContext";
import { Banner, Checkbox, Divider, NumberField, Row, Section, Select, UnitField, loadUnitOptions } from "./fields";
import type { FormProps } from "./forms.types";
import { useLoaded } from "./useLoaded";
import { useNodeForm } from "./useNodeForm";

interface Q {
  value: number;
  unit: string;
}
interface Stab {
  delta: Q;
  window: Q;
}
interface Overrides {
  min_duration: Q | null;
  role_max: Record<string, Q>;
  stabilisation: Record<string, Stab>;
}

const DURATION_UNITS: Array<[string, string]> = [
  ["h", "h"],
  ["min", "min"],
];
const DEFAULT_MIN_DURATION: Q = { value: 4, unit: "h" };
const DEFAULT_DELTA = 2;
const DEFAULT_WINDOW_MIN = 60;

/** "0.07874" style: 4 significant digits, "—" for an unknown value. */
const g4 = (q: Quantity | null | undefined): string =>
  q === null || q === undefined ? "—" : localizeNumber(String(Number(q.value.toPrecision(4))));

function asOverrides(v: unknown): Overrides {
  const o = (v && typeof v === "object" ? v : {}) as Partial<Overrides>;
  return {
    min_duration: o.min_duration ?? null,
    role_max: o.role_max ?? {},
    stabilisation: o.stabilisation ?? {},
  };
}

function stabText(st: MrtCheckRow["stabilisation"]): string {
  if (!st) return "—";
  const mark = st.ok === null ? "" : st.ok ? " ✓" : " ✗";
  const win = st.window ? ` / ${g4(st.window)} ${st.window.unit}` : "";
  const rel = st.relative_to_ambient ? " (rise above ambient)" : "";
  const info = st.required === false ? " (information)" : "";
  return `${g4(st.change)} ≤ ${g4(st.allowed)} ${st.allowed?.unit ?? ""}${win}${rel}${mark}${info}`;
}

const statusClass = (status: string): string =>
  status === "pass"
    ? "v-pass"
    : status === "fail"
      ? "v-fail"
      : status === "not evaluated"
        ? "v-warn"
        : "v-info";

const qText = (q: Quantity | null | undefined, unit: string): string =>
  q === null || q === undefined ? "—" : `${g4(q)} ${unit}`;

function RulesTable({ rules }: { rules: MrtRuleRow[] }) {
  return (
    <div className="grid-wrap">
      <table className="grid" aria-label="Bearing temperature rules">
        <thead>
          <tr>
            <th className="grid-text">Bearing temperature rule</th>
            <th>Worst</th>
            <th>Limit</th>
            <th>Status</th>
            <th className="grid-text">Note</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((r) => (
            <tr key={r.key}>
              <td className="grid-text">{r.name}</td>
              <td>{qText(r.value, r.unit)}</td>
              <td>{r.limit ? `≤ ${qText(r.limit, r.unit)}` : "—"}</td>
              <td className={statusClass(r.status)}>{r.status.toUpperCase()}</td>
              <td className="grid-text">{r.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** MRT Check — mirrors pumpflow/nodes/mechanical_run_check.py (verdict, channel table, overrides). */
export default function MrtCheckForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const view = (result?.view ?? {}) as Partial<MrtCheckView>;
  const options = useLoaded((e) => e.mrtOptions(), {
    roles: [] as string[],
    dimensions: [] as string[],
    role_dimensions: {} as Record<string, string>,
  });
  const [open, setOpen] = useState<boolean | null>(null);
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const ov = asOverrides(s.overrides);
  const anyOverride =
    ov.min_duration !== null ||
    Object.keys(ov.role_max).length > 0 ||
    Object.keys(ov.stabilisation).length > 0;
  const expanded = open ?? anyOverride;
  const write = (patch: Partial<Overrides>) => update({ overrides: { ...ov, ...patch } });

  const withKey = <T,>(rec: Record<string, T>, key: string, value: T | null): Record<string, T> => {
    const next = { ...rec };
    if (value === null) delete next[key];
    else next[key] = value;
    return next;
  };
  const firstUnit = async (dimension: string): Promise<string> =>
    (await loadUnitOptions(engine, dimension))[0]?.[0] ?? "";

  const setMax = (role: string, dimension: string, on: boolean) => {
    if (!on) {
      write({ role_max: withKey(ov.role_max, role, null) });
      return;
    }
    firstUnit(dimension).then(
      (unit) => write({ role_max: withKey(ov.role_max, role, { value: 0, unit }) }),
      () => undefined,
    );
  };
  const setStab = (role: string, dimension: string, on: boolean) => {
    if (!on) {
      write({ stabilisation: withKey(ov.stabilisation, role, null) });
      return;
    }
    firstUnit(dimension).then(
      (unit) =>
        write({
          stabilisation: withKey(ov.stabilisation, role, {
            delta: { value: DEFAULT_DELTA, unit },
            window: { value: DEFAULT_WINDOW_MIN, unit: "min" },
          }),
        }),
      () => undefined,
    );
  };

  const hasResult = view.verdict !== undefined;
  const tone = !hasResult
    ? "idle"
    : view.passed
      ? view.fully_assessed
        ? "ok"
        : "warn"
      : "error";
  const rows = view.rows ?? [];
  const limitedRoles = options.roles.filter((r) => options.role_dimensions[r]);

  return (
    <div className="form-body">
      <Section title="Verdict" />
      <div className={`verdict-banner verdict-${tone}`} role="status">
        {hasResult ? `${view.verdict_label}   ·   ${view.pump_tag}` : "—  awaiting a log"}
      </div>
      {!hasResult && result && <Banner kind="info">{result.status}</Banner>}
      {hasResult && (
        <>
          {view.inputs_text && <p className="field-hint">{view.inputs_text}</p>}
          <div>
            {`Duration ${g4(view.duration)} ${view.duration?.unit ?? ""}`}
            {view.min_duration
              ? ` (minimum ${g4(view.min_duration)} ${view.min_duration.unit}): `
              : " (no minimum): "}
            <span className={statusClass(view.duration_status ?? "")}>
              {(view.duration_status ?? "").toUpperCase()}
            </span>
          </div>
          {view.verified === false && (
            <p className="v-warn">
              ⚠ Limits not verified against the standard text or overridden: the verdict is
              provisional.
            </p>
          )}
          {view.criteria_label && <div>{`Criteria: ${view.criteria_label}`}</div>}
          <div className="grid-wrap">
            <table className="grid" aria-label="Channel results">
              <thead>
                <tr>
                  {["Channel", "Role", "Unit", "Min", "Max", "Last", "Limit", "Stabilisation", "Status"].map(
                    (h, i) => (
                      <th key={h} className={i === 0 || i === 1 || i === 7 ? "grid-text" : undefined}>
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.name}>
                    <td className="grid-text">{r.name}</td>
                    <td className="grid-text">{r.role}</td>
                    <td>{r.unit}</td>
                    <td>{g4(r.min)}</td>
                    <td>{g4(r.max)}</td>
                    <td>{g4(r.last)}</td>
                    <td>{g4(r.limit)}</td>
                    <td className="grid-text">{stabText(r.stabilisation)}</td>
                    <td className={statusClass(r.status)}>{r.status.toUpperCase()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(view.rules?.length ?? 0) > 0 && <RulesTable rules={view.rules ?? []} />}
          {view.source && (
            <details className="source-note">
              <summary>Source of the limits</summary>
              <p className="field-hint">{view.source}</p>
            </details>
          )}
        </>
      )}
      {error && <Banner kind="error">{error}</Banner>}
      <Divider />

      <button
        type="button"
        className="section-toggle"
        aria-expanded={expanded}
        onClick={() => setOpen(!expanded)}
      >
        <span aria-hidden="true">{expanded ? "▾" : "▸"}</span>
        Criteria overrides (unticked = criteria from the standard)
      </button>
      {expanded && (
        <div className="form-body">
          <Checkbox
            checked={ov.min_duration !== null}
            label="Min duration"
            onChange={(on) => write({ min_duration: on ? DEFAULT_MIN_DURATION : null })}
          />
          <Row label="Min duration value" disabled={ov.min_duration === null}>
            <span className="unit-field">
              <NumberField
                value={ov.min_duration ? ov.min_duration.value : null}
                disabled={ov.min_duration === null}
                ariaLabel="Min duration value"
                onChange={(v) =>
                  write({
                    min_duration: { value: v ?? 0, unit: ov.min_duration?.unit ?? "h" },
                  })
                }
              />
              <Select
                value={ov.min_duration?.unit ?? "h"}
                options={DURATION_UNITS}
                disabled={ov.min_duration === null}
                ariaLabel="Min duration unit"
                onChange={(unit) =>
                  write({ min_duration: { value: ov.min_duration?.value ?? 0, unit } })
                }
              />
            </span>
          </Row>
          {limitedRoles.map((role) => {
            const dimension = options.role_dimensions[role] ?? "";
            const mx = ov.role_max[role];
            const st = ov.stabilisation[role];
            return (
              <div key={role} className="override-role">
                <span className="section-label">{role}</span>
                <Checkbox
                  checked={mx !== undefined}
                  label={`${role} max`}
                  onChange={(on) => setMax(role, dimension, on)}
                />
                <Row label={`${role} max value`} disabled={!mx}>
                  <UnitField
                    dimension={dimension}
                    value={mx ? mx.value : null}
                    unit={mx?.unit ?? ""}
                    disabled={!mx}
                    onChange={(v, unit) =>
                      write({
                        role_max: withKey(ov.role_max, role, { value: v ?? 0, unit }),
                      })
                    }
                  />
                </Row>
                <Checkbox
                  checked={st !== undefined}
                  label={`${role} stabilisation`}
                  onChange={(on) => setStab(role, dimension, on)}
                />
                <Row label={`${role} stab. Δ ≤`} disabled={!st}>
                  <UnitField
                    dimension={dimension}
                    value={st ? st.delta.value : null}
                    unit={st?.delta.unit ?? ""}
                    disabled={!st}
                    onChange={(v, unit) =>
                      st &&
                      write({
                        stabilisation: withKey(ov.stabilisation, role, {
                          ...st,
                          delta: { value: v ?? 0, unit },
                        }),
                      })
                    }
                  />
                </Row>
                <Row label={`${role} min window`} suffix="min" disabled={!st}>
                  <NumberField
                    value={st ? st.window.value : null}
                    disabled={!st}
                    onChange={(v) =>
                      st &&
                      write({
                        stabilisation: withKey(ov.stabilisation, role, {
                          ...st,
                          window: { value: v ?? 0, unit: "min" },
                        }),
                      })
                    }
                  />
                </Row>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
