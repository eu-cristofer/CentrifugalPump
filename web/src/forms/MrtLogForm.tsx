import { type ClipboardEvent, type MouseEvent, useEffect, useRef, useState } from "react";
import type { MrtColumn, MrtRow } from "../engine/types";
import { useEngine } from "./engineContext";
import { Banner, Divider, NumberField, Row, Section, Select, TextField, UnitSelect } from "./fields";
import type { FormProps } from "./forms.types";
import { getStr } from "./settings";
import { useLoaded } from "./useLoaded";
import { useNodeForm } from "./useNodeForm";

/** A channel name edited as a draft: committed on blur/Enter when non-empty and unique. */
function NameInput({
  name,
  taken,
  ariaLabel,
  onCommit,
}: {
  name: string;
  taken: string[];
  ariaLabel: string;
  onCommit: (next: string) => void;
}) {
  const [draft, setDraft] = useState(name);
  useEffect(() => setDraft(name), [name]);
  const commit = () => {
    const next = draft.trim();
    if (!next || next === name || taken.includes(next)) setDraft(name);
    else onCommit(next);
  };
  return (
    <input
      className="field"
      type="text"
      value={draft}
      aria-label={ariaLabel}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
      }}
    />
  );
}

/** MRT Log — mirrors pumpflow/nodes/mechanical_run.py (channels + time-stamped readings). */
export default function MrtLogForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const options = useLoaded((e) => e.mrtOptions(), {
    roles: [] as string[],
    dimensions: [] as string[],
    role_dimensions: {} as Record<string, string>,
  });
  const [selected, setSelected] = useState<number[]>([]);
  const anchor = useRef(0);
  const convSeq = useRef(0);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const cols: MrtColumn[] = Array.isArray(s.columns) ? (s.columns as MrtColumn[]) : [];
  const rows: MrtRow[] = Array.isArray(s.rows) ? (s.rows as MrtRow[]) : [];

  // ---- readings ------------------------------------------------------------------
  const setRows = (next: MrtRow[]) => update({ rows: next });
  const setTime = (i: number, time: string) =>
    setRows(rows.map((r, j) => (j === i ? { ...r, time } : r)));
  const setValue = (i: number, name: string, v: number | null) =>
    setRows(
      rows.map((r, j) => (j === i ? { ...r, values: { ...(r.values ?? {}), [name]: v } } : r)),
    );

  const addReading = () => {
    engine.nextTime(rows).then(
      (time) => setRows([...rows, { time, values: {} }]),
      () => undefined,
    );
  };
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

  // ---- paste ---------------------------------------------------------------------
  const applyPaste = (text: string) => {
    if (!text.trim()) return;
    engine.parseMrtPaste(text, cols).then(
      (parsed) => {
        if (parsed.length === 0) return;
        update({ rows: parsed });
        setSelected([]);
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

  // ---- channels ------------------------------------------------------------------
  const setCols = (next: MrtColumn[], nextRows: MrtRow[] = rows) =>
    update({ columns: next, rows: nextRows });
  const patchCol = (j: number, patch: Partial<MrtColumn>) =>
    setCols(cols.map((c, k) => (k === j ? { ...c, ...patch } : c)));

  const changeUnit = (j: number, next: string) => {
    const c = cols[j];
    if (!c || next === c.unit) return;
    const id = ++convSeq.current;
    Promise.all(
      rows.map(async (r) => {
        const v = r.values?.[c.name];
        if (v === null || v === undefined) return r;
        const converted = (await engine.convert(v, c.unit, next, c.dimension)) ?? v;
        return { ...r, values: { ...r.values, [c.name]: converted } };
      }),
    ).then(
      (converted) => {
        if (id === convSeq.current) {
          setCols(
            cols.map((x, k) => (k === j ? { ...x, unit: next } : x)),
            converted,
          );
        }
      },
      () => undefined,
    );
  };

  const changeDimension = (j: number, dimension: string) => {
    const c = cols[j];
    if (!c || dimension === c.dimension) return;
    engine.unitOptions(dimension).then(
      (opts) => patchCol(j, { dimension, unit: opts[0]?.[0] ?? c.unit }),
      () => undefined,
    );
  };

  const rename = (j: number, next: string) => {
    const old = cols[j]?.name;
    if (old === undefined) return;
    const renamed = rows.map((r) => {
      const values = { ...(r.values ?? {}) };
      if (old in values) {
        values[next] = values[old] ?? null;
        delete values[old];
      }
      return { ...r, values };
    });
    setCols(
      cols.map((c, k) => (k === j ? { ...c, name: next } : c)),
      renamed,
    );
  };

  const addChannel = () => {
    let n = cols.length + 1;
    while (cols.some((c) => c.name === `Channel ${n}`)) n += 1;
    engine.unitOptions("temperature").then(
      (opts) =>
        setCols([
          ...cols,
          {
            name: `Channel ${n}`,
            dimension: "temperature",
            unit: opts[0]?.[0] ?? "°C",
            role: "other",
          },
        ]),
      () => undefined,
    );
  };

  const removeChannel = (j: number) => {
    const name = cols[j]?.name;
    if (name === undefined) return;
    setCols(
      cols.filter((_, k) => k !== j),
      rows.map((r) => {
        const values = { ...(r.values ?? {}) };
        delete values[name];
        return { ...r, values };
      }),
    );
  };

  const state = result?.state;
  return (
    <div className="form-body">
      <Section title="Pump identity" />
      <Row label="Pump TAG">
        <TextField
          value={getStr(s, "pump_tag")}
          placeholder="physical unit TAG, e.g. P-9001A"
          onChange={(v) => update({ pump_tag: v })}
        />
      </Row>
      <Divider />

      <Section title="Readings" />
      <div className="tool-bar">
        <button type="button" className="tool-button" onClick={addReading}>
          ＋ Add reading
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
          <label htmlFor="mrt-paste-text" className="field-hint">
            Paste the spreadsheet cells here (tab separated: time, then one column per channel;
            an optional header line names the channels and units).
          </label>
          <textarea
            id="mrt-paste-text"
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
        <table className="grid" aria-label="Readings">
          <thead>
            <tr>
              <th />
              <th />
              {cols.map((c, j) => (
                <th key={c.name}>
                  <UnitSelect
                    dimension={c.dimension}
                    unit={c.unit}
                    ariaLabel={`${c.name} unit`}
                    onPick={(next) => changeUnit(j, next)}
                  />
                </th>
              ))}
            </tr>
            <tr>
              <th>#</th>
              <th>Time</th>
              {cols.map((c) => (
                <th key={c.name}>{c.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className={selected.includes(i) ? "selected" : undefined}>
                <th scope="row">
                  <button
                    type="button"
                    className="row-select"
                    aria-label={`Select reading ${i + 1}`}
                    aria-pressed={selected.includes(i)}
                    onClick={(e) => selectRow(i, e)}
                  >
                    {i + 1}
                  </button>
                </th>
                <td>
                  <TextField
                    value={r.time ?? ""}
                    placeholder="HH:MM"
                    ariaLabel={`Time reading ${i + 1}`}
                    onChange={(v) => setTime(i, v)}
                  />
                </td>
                {cols.map((c) => (
                  <td key={c.name}>
                    <NumberField
                      value={r.values?.[c.name] ?? null}
                      ariaLabel={`${c.name} reading ${i + 1}`}
                      onChange={(v) => setValue(i, c.name, v)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="field-hint">Add reading pre-fills the next time, 15 minutes after the last.</p>
      {state === "invalid" && result ? (
        <Banner kind="error">{result.status}</Banner>
      ) : (
        result && <Banner kind={state === "ok" ? "ok" : "info"}>{result.status}</Banner>
      )}
      {error && <Banner kind="error">{error}</Banner>}
      <Divider />

      <Section title="Channels (name, dimension, role)" />
      <div className="tool-bar">
        <button type="button" className="tool-button" onClick={addChannel}>
          ＋ Channel
        </button>
      </div>
      <div className="grid-wrap">
        <table className="grid" aria-label="Channels">
          <thead>
            <tr>
              <th className="grid-text">Name</th>
              <th className="grid-text">Dimension</th>
              <th className="grid-text">Role</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cols.map((c, j) => (
              <tr key={j}>
                <td>
                  <NameInput
                    name={c.name}
                    taken={cols.filter((_, k) => k !== j).map((x) => x.name)}
                    ariaLabel={`Channel ${j + 1} name`}
                    onCommit={(next) => rename(j, next)}
                  />
                </td>
                <td>
                  <Select
                    value={c.dimension}
                    options={options.dimensions.map((d): [string, string] => [d, d])}
                    ariaLabel={`Channel ${j + 1} dimension`}
                    onChange={(d) => changeDimension(j, d)}
                  />
                </td>
                <td>
                  <Select
                    value={c.role}
                    options={options.roles.map((r): [string, string] => [r, r])}
                    ariaLabel={`Channel ${j + 1} role`}
                    onChange={(r) => patchCol(j, { role: r })}
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="tool-button"
                    aria-label={`Remove channel ${j + 1}`}
                    onClick={() => removeChannel(j)}
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
