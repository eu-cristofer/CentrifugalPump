import { type ClipboardEvent, type MouseEvent, useRef, useState } from "react";
import type { TestPointsView, TestRowData } from "../engine/types";
import { useEngine } from "./engineContext";
import {
  Banner,
  Checkbox,
  Divider,
  InfoButton,
  NumberField,
  Row,
  Section,
  Select,
  TextField,
  UnitField,
  useUnitOptions,
} from "./fields";
import type { FormProps } from "./forms.types";
import { getNumOrNull, getStr } from "./settings";
import { useNodeForm } from "./useNodeForm";

const DEFAULT_FLUID = "__default__";
const DEFAULT_LABEL = "Water at T_water";

interface Col {
  key: string;
  name: string;
  dimension: string;
  /** computed by Python from the other columns: shown read-only */
  computed?: boolean;
  tooltip?: string;
}

// Mirrors pumpflow/nodes/test_points.py (_NAMES / _ALL_KEYS) and units.ALL_COLUMN_DIMENSIONS.
const HYDRAULIC: Col[] = [
  { key: "q", name: "Q", dimension: "capacity" },
  { key: "p_suc", name: "P_suc", dimension: "pressure" },
  { key: "p_dis", name: "P_dis", dimension: "pressure" },
  { key: "temp_c", name: "T_water", dimension: "temperature" },
  { key: "n", name: "N", dimension: "speed" },
  { key: "power", name: "P", dimension: "power" },
  { key: "head", name: "Head", dimension: "head", computed: true },
  { key: "eff", name: "η", dimension: "efficiency", computed: true },
];
const FALLBACK_UNIT: Record<string, string> = {
  q: "m³/h",
  p_suc: "bar",
  p_dis: "bar",
  temp_c: "°C",
  n: "rpm",
  power: "kW",
  head: "m",
  eff: "%",
};
const VIB_FALLBACK_UNIT = "mm/s";
const ROW_KEYS = HYDRAULIC.map((c) => c.key);

const GEO: Array<{ key: string; label: string; isId: boolean }> = [
  { key: "suction_id", label: "Suction pipe ID", isId: true },
  { key: "discharge_id", label: "Discharge pipe ID", isId: true },
  { key: "suction_z", label: "Suction gauge elevation z_s", isId: false },
  { key: "discharge_z", label: "Discharge gauge elevation z_d", isId: false },
];

const blankRow = (): TestRowData => Object.fromEntries(ROW_KEYS.map((k) => [k, null]));

/** "12.346" style: fixed decimals, "—" for an unknown value. */
const show = (v: number | null | undefined, decimals: number): string =>
  v === null || v === undefined ? "—" : v.toFixed(decimals);

function ColumnUnit({
  dimension,
  unit,
  label,
  onPick,
}: {
  dimension: string;
  unit: string;
  label: string;
  onPick: (next: string) => void;
}) {
  const options = useUnitOptions(dimension);
  return (
    <Select
      value={unit}
      options={options.map(([l]): [string, string] => [l, l])}
      ariaLabel={`${label} unit`}
      onChange={onPick}
    />
  );
}

/** Test Points Table — mirrors pumpflow/nodes/test_points.py (UI_SPEC §5.2, §12). */
export default function TestPointsForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const view = (result?.view ?? {}) as Partial<TestPointsView>;
  const [selected, setSelected] = useState<number[]>([]);
  const anchor = useRef(0);
  const convSeq = useRef(0);
  const [vibOn, setVibOn] = useState<boolean | null>(null);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [notice, setNotice] = useState("");
  const [geoDraft, setGeoDraft] = useState<Record<string, number | null>>({});

  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const rows: TestRowData[] = Array.isArray(s.rows) ? (s.rows as TestRowData[]) : [];
  const cols: Record<string, string> =
    s.columns && typeof s.columns === "object" ? (s.columns as Record<string, string>) : {};
  const pressureRef = getStr(s, "pressure_ref", "g");
  const unitOf = (key: string): string =>
    cols[key] ?? FALLBACK_UNIT[key] ?? VIB_FALLBACK_UNIT;
  const vibColumns = view.vib_columns ?? [];
  const hasVibData = rows.some((r) => vibColumns.some((c) => r[c.key] != null));
  const showVib = vibOn ?? hasVibData;
  const shownCols: Col[] = [
    ...HYDRAULIC,
    ...(showVib
      ? vibColumns.map(
          (c): Col => ({
            key: c.key,
            name: c.title,
            dimension: "vibration_velocity",
            tooltip: c.tooltip,
          }),
        )
      : []),
  ];

  // ---- rows --------------------------------------------------------------------
  const setRows = (next: TestRowData[]) => update({ rows: next });
  const setCell = (i: number, key: string, v: number | null) =>
    setRows(rows.map((r, j) => (j === i ? { ...r, [key]: v } : r)));

  const selectRow = (i: number, e: MouseEvent) => {
    if (e.shiftKey) {
      const [a, b] = [Math.min(anchor.current, i), Math.max(anchor.current, i)];
      setSelected(Array.from({ length: b - a + 1 }, (_, k) => a + k));
      return;
    }
    anchor.current = i;
    if (e.ctrlKey || e.metaKey) {
      setSelected((cur) => (cur.includes(i) ? cur.filter((x) => x !== i) : [...cur, i]));
    } else {
      setSelected([i]);
    }
  };

  const addRow = () => setRows([...rows, blankRow()]);
  const removeRows = () => {
    if (selected.length === 0) return;
    setRows(rows.filter((_, i) => !selected.includes(i)));
    setSelected([]);
  };
  const move = (delta: number) => {
    const picked = [...selected].sort((a, b) => a - b);
    if (picked.length === 0) return;
    const next = [...rows];
    const moved: number[] = [];
    for (const idx of delta < 0 ? picked : [...picked].reverse()) {
      const j = idx + delta;
      if (j >= 0 && j < next.length && !picked.includes(j)) {
        [next[idx], next[j]] = [next[j]!, next[idx]!];
        moved.push(j);
      } else {
        moved.push(idx);
      }
    }
    setRows(next);
    setSelected(moved);
  };

  // ---- units -------------------------------------------------------------------
  const changeUnit = (keys: string[], dimension: string, next: string) => {
    const old = unitOf(keys[0]!);
    if (next === old) return;
    const id = ++convSeq.current;
    Promise.all(
      rows.map(async (r) => {
        const out = { ...r };
        for (const k of keys) {
          const v = out[k];
          if (v !== null && v !== undefined) {
            out[k] = (await engine.convert(v, old, next, dimension)) ?? v;
          }
        }
        return out;
      }),
    ).then(
      (converted) => {
        if (id !== convSeq.current) return;
        const nextCols = { ...cols };
        for (const k of keys) nextCols[k] = next;
        update({ rows: converted, columns: nextCols });
      },
      () => undefined,
    );
  };

  const changeRef = (next: string) => {
    if (next === pressureRef) return;
    engine.atmosphere(unitOf("p_suc")).then(
      (atm) => {
        const delta = next === "a" ? atm : -atm;
        const shifted = rows.map((r) => {
          const out = { ...r };
          for (const k of ["p_suc", "p_dis"]) {
            const v = out[k];
            if (v !== null && v !== undefined) out[k] = v + delta;
          }
          return out;
        });
        update({ rows: shifted, pressure_ref: next });
      },
      () => undefined,
    );
  };

  // ---- paste -------------------------------------------------------------------
  const applyPaste = (text: string) => {
    if (!text.trim()) return;
    engine.parsePaste(text, { ...cols }, pressureRef).then(
      (res) => {
        if (res.rows.length === 0) return;
        update({
          rows: res.rows,
          columns: { ...cols, ...res.columns },
          pressure_ref: res.pressure_ref,
        });
        setSelected([]);
        if (res.vibration) setVibOn(true);
        setNotice(res.warnings.join(" "));
        setPasteOpen(false);
        setPasteText("");
      },
      () => undefined,
    );
  };

  const pasteFromClipboard = () => {
    const clip = typeof navigator !== "undefined" ? navigator.clipboard : undefined;
    if (!clip || typeof clip.readText !== "function") {
      setPasteOpen(true);
      return;
    }
    clip.readText().then(applyPaste, () => setPasteOpen(true));
  };

  const onGridPaste = (e: ClipboardEvent) => {
    const text = e.clipboardData.getData("text");
    if (/[\t\n;]/.test(text.trim())) {
      e.preventDefault();
      applyPaste(text);
    }
  };

  // ---- bench geometry ----------------------------------------------------------
  const applied = GEO.some((g) => getNumOrNull(s, g.key) !== null);
  const geoValue = (key: string): number | null =>
    applied ? getNumOrNull(s, key) : (geoDraft[key] ?? 0);
  const geoUnit = (key: string, isId: boolean) => getStr(s, `${key}_unit`, isId ? "mm" : "m");
  const applyGeometry = (on: boolean) => {
    const patch: Record<string, unknown> = {};
    for (const g of GEO) {
      patch[g.key] = on ? (geoDraft[g.key] ?? getNumOrNull(s, g.key) ?? 0) : null;
      patch[`${g.key}_unit`] = geoUnit(g.key, g.isId);
    }
    update(patch);
  };
  const onGeoChange = (key: string, v: number | null, u: string) => {
    setGeoDraft((d) => ({ ...d, [key]: v }));
    if (applied) update({ [key]: v ?? 0, [`${key}_unit`]: u });
    else update({ [`${key}_unit`]: u });
  };

  // ---- status ------------------------------------------------------------------
  const state = result?.state;
  const testFluid = view.test_fluid ?? null;
  const fluids = view.fluids ?? [];

  const headTip = (i: number): string | undefined => {
    const c = view.rows?.[i]?.components;
    if (!c) return undefined;
    const f = (v: number | null | undefined) => (v === null || v === undefined ? "—" : v.toFixed(3));
    return `pressure ${f(c.pressure)} + velocity ${f(c.velocity)} + elevation ${f(c.elevation)} = ${f(c.total)} ${unitOf("head")}`;
  };

  return (
    <div className="form-body">
      <Section title="Pump identity" />
      <Row label="Pump TAG">
        <TextField
          value={getStr(s, "pump_tag")}
          placeholder="physical unit TAG, e.g. B-2351105A"
          onChange={(v) => update({ pump_tag: v })}
        />
      </Row>
      <Row label="Pressure reference">
        <Select
          value={pressureRef}
          options={[
            ["g (gauge)", "g"],
            ["a (absolute)", "a"],
          ]}
          onChange={changeRef}
        />
      </Row>
      {fluids.length > 0 && (
        <Row label="Fluid source">
          <Select
            value={view.choice ?? DEFAULT_FLUID}
            options={[[DEFAULT_LABEL, DEFAULT_FLUID], ...fluids.map((f): [string, string] => [f, f])]}
            onChange={(v) => update({ fluid_choice: v })}
          />
        </Row>
      )}
      <Divider />

      <Section title="Test bench geometry (optional)" />
      <Checkbox checked={applied} label="Apply bench geometry" onChange={applyGeometry} />
      {GEO.map((g) => (
        <Row key={g.key} label={g.label} disabled={!applied}>
          <UnitField
            dimension="length"
            value={geoValue(g.key)}
            unit={geoUnit(g.key, g.isId)}
            disabled={!applied}
            onChange={(v, u) => onGeoChange(g.key, v, u)}
          />
        </Row>
      ))}
      <Divider />

      <Section title="Measured points" />
      <Checkbox
        checked={showVib}
        label={view.vib_label ?? "Vibration columns (RMS, overall / filtered)"}
        onChange={(v) => setVibOn(v)}
      />
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
        <button
          type="button"
          className="tool-button"
          disabled={selected.length === 0}
          onClick={() => move(-1)}
        >
          ↑ Up
        </button>
        <button
          type="button"
          className="tool-button"
          disabled={selected.length === 0}
          onClick={() => move(1)}
        >
          ↓ Down
        </button>
        <button type="button" className="tool-button" onClick={pasteFromClipboard}>
          ⎘ Paste
        </button>
      </div>
      {pasteOpen && (
        <div className="paste-box">
          <label htmlFor="paste-text" className="field-hint">
            Paste the spreadsheet cells here (tab separated, optional unit header line).
          </label>
          <textarea
            id="paste-text"
            className="field"
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
          />
          <div className="tool-bar">
            <button type="button" className="tool-button" onClick={() => applyPaste(pasteText)}>
              Apply
            </button>
            <button type="button" className="tool-button" onClick={() => setPasteOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid-wrap" onPaste={onGridPaste}>
        <table className="grid" aria-label="Measured points">
          <thead>
            <tr>
              <th />
              {shownCols.map((c) => {
                if (c.key === "p_dis") return null;
                const keys = c.key === "p_suc" ? ["p_suc", "p_dis"] : [c.key];
                return (
                  <th key={c.key} colSpan={keys.length}>
                    <ColumnUnit
                      dimension={c.dimension}
                      unit={unitOf(c.key)}
                      label={keys.length > 1 ? "Pressure" : c.name}
                      onPick={(next) => changeUnit(keys, c.dimension, next)}
                    />
                  </th>
                );
              })}
            </tr>
            <tr>
              <th>#</th>
              {shownCols.map((c) => (
                <th key={c.key} title={c.tooltip}>
                  {c.name}
                  {c.dimension === "pressure" ? ` ${pressureRef}` : ""}
                  {c.key === "head" && <InfoButton infoKey="head" />}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={selected.includes(i) ? "selected" : undefined}>
                <th scope="row">
                  <button
                    type="button"
                    className="row-select"
                    aria-label={`Select row ${i + 1}`}
                    aria-pressed={selected.includes(i)}
                    onClick={(e) => selectRow(i, e)}
                  >
                    {i + 1}
                  </button>
                </th>
                {shownCols.map((c) =>
                  c.computed ? (
                    <td
                      key={c.key}
                      className="computed"
                      title={c.key === "head" ? headTip(i) : undefined}
                      aria-label={`${c.name} row ${i + 1} (computed)`}
                    >
                      {c.key === "head"
                        ? show(view.rows?.[i]?.head, 2)
                        : show(view.rows?.[i]?.eff, 1)}
                    </td>
                  ) : (
                    <td key={c.key}>
                      <NumberField
                        value={row[c.key] ?? null}
                        ariaLabel={`${c.name} row ${i + 1}`}
                        onChange={(v) => setCell(i, c.key, v)}
                      />
                    </td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="field-hint">
        Head = ΔP/(ρ·g){view.rows?.some((r) => r.components) ? " + velocity + elevation" : ""} and
        η are computed from the other columns; edit the pressures, flow and power.
      </p>

      {notice && <Banner kind="warn">{notice}</Banner>}
      {error && <Banner kind="error">{error}</Banner>}
      {state === "invalid" && result && <Banner kind="error">{result.status}</Banner>}
      {state !== "invalid" && testFluid && (
        <Banner kind="info">
          {`Test fluid overridden by connected Fluid node (${Math.round(testFluid.density_kgm3 ?? 0)} kg/m³) — Head/η use it; T_water is informational.`}
        </Banner>
      )}
      {state === "ok" && !testFluid && view.has_shutoff === false && (
        <Banner kind="warn">
          OK — but no shut-off point (Q≈0). Shut-off head check will extrapolate.
        </Banner>
      )}
    </div>
  );
}
