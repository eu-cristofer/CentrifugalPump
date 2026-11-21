import { useRef, useState } from "react";
import { NpshChart } from "../charts/PerformanceChart";
import type { NpshView } from "../engine/types";
import { useEngine } from "./engineContext";
import {
  Banner,
  Checkbox,
  Divider,
  NumberField,
  Row,
  Section,
  Select,
  TextField,
  UnitField,
  UnitSelect,
} from "./fields";
import type { FormProps } from "./forms.types";
import { getNum, getNumOrNull, getStr } from "./settings";
import { useNodeForm } from "./useNodeForm";

interface NpshRow {
  q: number | null;
  npshr: number | null;
}

interface Overrides {
  min_ratio?: number | null;
  min_margin?: { value: number; unit: string } | null;
}

const MODES: Array<[string, string]> = [
  ["Direct NPSHr points", "points"],
  ["NPSHa calculator", "calculator"],
];
const DEGREES: Array<[string, string]> = ["1", "2", "3", "4", "5"].map((d) => [d, d]);

const fixed = (v: number | null | undefined, d: number): string =>
  v === null || v === undefined ? "—" : v.toFixed(d);

/** NPSH — mirrors pumpflow/nodes/npsh.py (NPSHr points, NPSHa, overrides, verdict). */
export default function NpshForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const view = (result?.view ?? {}) as Partial<NpshView>;
  const [selected, setSelected] = useState<number[]>([]);
  const convSeq = useRef(0);
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const rows: NpshRow[] = Array.isArray(s.rows) ? (s.rows as NpshRow[]) : [];
  const cols = (s.columns && typeof s.columns === "object" ? s.columns : {}) as Record<
    string,
    string
  >;
  const qUnit = cols.q ?? "m³/h";
  const nUnit = cols.npshr ?? "m";
  const mode = getStr(s, "mode", "points");
  const ov = (s.overrides && typeof s.overrides === "object" ? s.overrides : {}) as Overrides;

  // ---- points ------------------------------------------------------------------
  const setRows = (next: NpshRow[]) => update({ rows: next });
  const setCell = (i: number, key: "q" | "npshr", v: number | null) =>
    setRows(rows.map((r, j) => (j === i ? { ...r, [key]: v } : r)));
  const addRow = () => setRows([...rows, { q: null, npshr: null }]);
  const removeRows = () => {
    if (selected.length === 0) return;
    setRows(rows.filter((_, i) => !selected.includes(i)));
    setSelected([]);
  };
  const changeUnit = (key: "q" | "npshr", dimension: string, next: string) => {
    const old = key === "q" ? qUnit : nUnit;
    if (next === old) return;
    const id = ++convSeq.current;
    Promise.all(
      rows.map(async (r) => {
        const v = r[key];
        return v === null ? r : { ...r, [key]: (await engine.convert(v, old, next, dimension)) ?? v };
      }),
    ).then(
      (converted) => {
        if (id === convSeq.current) update({ rows: converted, columns: { ...cols, [key]: next } });
      },
      () => undefined,
    );
  };

  // ---- optional quantities (null = unset, stored as omitted) -----------------------
  const quotedOn = getNumOrNull(s, "npshr_quoted") !== null;
  const npshaOn = getNumOrNull(s, "npsha") !== null;
  const idOn = getNumOrNull(s, "calc_id") !== null;
  const writeOv = (patch: Overrides) => update({ overrides: { ...ov, ...patch } });
  const ratioOn = ov.min_ratio !== null && ov.min_ratio !== undefined;
  const marginOn = !!ov.min_margin;

  // ---- verdict -----------------------------------------------------------------
  const hasResult = view.status !== undefined;
  const tone = !hasResult
    ? "idle"
    : view.status === "pass"
      ? "ok"
      : view.status === "fail"
        ? "error"
        : "warn";
  const hasChart = !!view.curve && view.points !== undefined;

  return (
    <div className="form-body">
      <Section title="Pump identity" />
      <Row label="Pump TAG">
        <TextField
          value={getStr(s, "pump_tag")}
          placeholder="physical unit TAG, e.g. B-34004A"
          onChange={(v) => update({ pump_tag: v })}
        />
      </Row>
      <Divider />

      <Section title="NPSHr test points" />
      <div className="tool-bar">
        <button type="button" className="tool-button" onClick={addRow}>
          ＋ Add row
        </button>
        <button
          type="button"
          className="tool-button"
          disabled={selected.length === 0}
          onClick={removeRows}
        >
          － Remove
        </button>
      </div>
      <div className="grid-wrap">
        <table className="grid" aria-label="NPSHr points">
          <thead>
            <tr>
              <th />
              <th>
                <UnitSelect
                  dimension="capacity"
                  unit={qUnit}
                  ariaLabel="Capacity unit"
                  onPick={(u) => changeUnit("q", "capacity", u)}
                />
              </th>
              <th>
                <UnitSelect
                  dimension="npsh"
                  unit={nUnit}
                  ariaLabel="NPSHr unit"
                  onPick={(u) => changeUnit("npshr", "npsh", u)}
                />
              </th>
            </tr>
            <tr>
              <th>#</th>
              <th>Q</th>
              <th>NPSHr</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className={selected.includes(i) ? "selected" : undefined}>
                <th scope="row">
                  <button
                    type="button"
                    className="row-select"
                    aria-label={`Select row ${i + 1}`}
                    aria-pressed={selected.includes(i)}
                    onClick={() =>
                      setSelected((cur) =>
                        cur.includes(i) ? cur.filter((x) => x !== i) : [...cur, i],
                      )
                    }
                  >
                    {i + 1}
                  </button>
                </th>
                <td>
                  <NumberField
                    value={r.q}
                    ariaLabel={`Q row ${i + 1}`}
                    onChange={(v) => setCell(i, "q", v)}
                  />
                </td>
                <td>
                  <NumberField
                    value={r.npshr}
                    ariaLabel={`NPSHr row ${i + 1}`}
                    onChange={(v) => setCell(i, "npshr", v)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Row label="Fit degree">
        <Select
          value={String(getNum(s, "degree", 2))}
          options={DEGREES}
          onChange={(v) => update({ degree: Number(v) })}
        />
      </Row>
      <Checkbox
        checked={quotedOn}
        label="Judge against the quoted NPSHr (datasheet, at rated flow)"
        onChange={(on) =>
          update({
            npshr_quoted: on ? (getNumOrNull(s, "npshr_quoted") ?? view.npshr_quoted ?? 0) : null,
            npshr_quoted_unit: getStr(s, "npshr_quoted_unit", "m"),
          })
        }
      />
      <Row label="Quoted NPSHr" disabled={!quotedOn}>
        <UnitField
          dimension="npsh"
          value={getNumOrNull(s, "npshr_quoted")}
          unit={getStr(s, "npshr_quoted_unit", "m")}
          disabled={!quotedOn}
          onChange={(v, u) => update({ npshr_quoted: v ?? 0, npshr_quoted_unit: u })}
        />
      </Row>
      <Divider />

      <Section title="NPSHa" />
      <Row label="Source">
        <Select value={mode} options={MODES} onChange={(v) => update({ mode: v })} />
      </Row>
      {mode === "calculator" ? (
        <>
          <Row label="Suction pressure">
            <UnitField
              dimension="pressure"
              value={getNum(s, "calc_p", 1.2)}
              unit={getStr(s, "calc_p_unit", "bar")}
              onChange={(v, u) => update({ calc_p: v ?? 0, calc_p_unit: u })}
            />
          </Row>
          <Row label="Pressure reference">
            <Select
              value={getStr(s, "calc_p_ref", "a")}
              options={[
                ["g (gauge)", "g"],
                ["a (absolute)", "a"],
              ]}
              onChange={(v) => update({ calc_p_ref: v })}
            />
          </Row>
          <Row label="Water temperature">
            <UnitField
              dimension="temperature"
              value={getNum(s, "calc_temp", 20)}
              unit={getStr(s, "calc_temp_unit", "°C")}
              onChange={(v, u) => update({ calc_temp: v ?? 0, calc_temp_unit: u })}
            />
          </Row>
          <Checkbox
            checked={idOn}
            label="Suction pipe ID (adds velocity head)"
            onChange={(on) =>
              update({
                calc_id: on ? (getNumOrNull(s, "calc_id") ?? 100) : null,
                calc_id_unit: getStr(s, "calc_id_unit", "mm"),
              })
            }
          />
          <Row label="Suction ID" disabled={!idOn}>
            <UnitField
              dimension="length"
              value={getNumOrNull(s, "calc_id")}
              unit={getStr(s, "calc_id_unit", "mm")}
              disabled={!idOn}
              onChange={(v, u) => update({ calc_id: v ?? 0, calc_id_unit: u })}
            />
          </Row>
          <Row label="Suction elevation z">
            <UnitField
              dimension="length"
              value={getNum(s, "calc_z", 0)}
              unit={getStr(s, "calc_z_unit", "m")}
              onChange={(v, u) => update({ calc_z: v ?? 0, calc_z_unit: u })}
            />
          </Row>
          {view.npsha !== undefined && view.npsha !== null && (
            <pre className="mono-block">{`Calculated NPSHa: ${view.npsha.toFixed(3)} m`}</pre>
          )}
        </>
      ) : (
        <>
          <Checkbox
            checked={npshaOn}
            label="Enter NPSHa here (else the rated point's)"
            onChange={(on) =>
              update({
                npsha: on ? (getNumOrNull(s, "npsha") ?? view.npsha ?? 0) : null,
                npsha_unit: getStr(s, "npsha_unit", "m"),
              })
            }
          />
          <Row label="NPSHa" disabled={!npshaOn}>
            <UnitField
              dimension="npsh"
              value={getNumOrNull(s, "npsha")}
              unit={getStr(s, "npsha_unit", "m")}
              disabled={!npshaOn}
              onChange={(v, u) => update({ npsha: v ?? 0, npsha_unit: u })}
            />
          </Row>
        </>
      )}
      <Divider />

      <Section title="Criteria overrides (blank = library criteria)" />
      <Checkbox
        checked={ratioOn}
        label="Min NPSHa / NPSHr ratio"
        onChange={(on) => writeOv({ min_ratio: on ? (view.min_ratio ?? 1) : null })}
      />
      <Row label="Min ratio" disabled={!ratioOn}>
        <NumberField
          value={ratioOn ? (ov.min_ratio ?? null) : (view.min_ratio ?? 1)}
          disabled={!ratioOn}
          onChange={(v) => {
            if (v !== null && v >= 0) writeOv({ min_ratio: v });
          }}
        />
      </Row>
      <Checkbox
        checked={marginOn}
        label="Min margin NPSHa − NPSHr"
        onChange={(on) =>
          writeOv({
            min_margin: on ? { value: view.min_margin ?? 0, unit: "m" } : null,
          })
        }
      />
      <Row label="Min margin" disabled={!marginOn}>
        <UnitField
          dimension="npsh"
          value={ov.min_margin ? ov.min_margin.value : null}
          unit={ov.min_margin?.unit ?? "m"}
          disabled={!marginOn}
          onChange={(v, u) => writeOv({ min_margin: { value: v ?? 0, unit: u } })}
        />
      </Row>
      <Divider />

      <Section title="Verdict" />
      <div className={`verdict-banner verdict-${tone}`} role="status">
        {hasResult ? `${view.verdict}   ·   ${view.pump_tag}` : "—  awaiting inputs"}
      </div>
      {hasResult ? (
        <>
          <div>
            {`NPSHa ${fixed(view.npsha, 2)} m · NPSHr ${fixed(view.npshr, 2)} m · margin ${fixed(view.margin, 2)} m · ratio ${fixed(view.ratio, 2)}`}
          </div>
          {view.criteria_label && <div>{`Criteria: ${view.criteria_label}`}</div>}
          {view.quoted_ok !== null && view.quoted_ok !== undefined && (
            <div>
              {`Quoted NPSHr ${fixed(view.npshr_quoted, 2)} m: ${view.quoted_ok ? "OK ✓" : "EXCEEDED ✗"}`}
            </div>
          )}
          {view.verified === false && view.status !== "info" && (
            <p className="v-warn">⚠ Criteria not verified against the standard text: provisional.</p>
          )}
        </>
      ) : (
        <Banner kind="info">{result?.status ?? ""}</Banner>
      )}
      {error && <Banner kind="error">{error}</Banner>}
      {hasChart && view.curve && (
        <NpshChart
          npsh={{
            points: view.points ?? null,
            curve: view.curve,
            npsha: view.npsha ?? null,
            npshr_quoted: view.npshr_quoted ?? null,
          }}
          ratedQ={view.rated_q ?? null}
        />
      )}
    </div>
  );
}
