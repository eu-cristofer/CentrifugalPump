import type { PerformancePlotView, Settings } from "../engine/types";
import PerformanceChart from "../charts/PerformanceChart";
import type { PanelKey } from "../charts/panels";
import { useEngine } from "./engineContext";
import { Banner, Checkbox, Divider, Row, Section, UnitField, useConvertedMany } from "./fields";
import type { FormProps } from "./forms.types";
import { getBool, getStr } from "./settings";
import { useNodeForm } from "./useNodeForm";

/** key, title, units dimension, settings key, unit settings key, default [lo, hi] (canonical). */
const YLIMS: Array<{
  key: PanelKey;
  title: string;
  dimension: string;
  skey: string;
  ukey: string;
  canon: string;
  fallback: [number, number];
  optional: boolean;
}> = [
  { key: "head", title: "Head", dimension: "head", skey: "head_ylim", ukey: "head_ylim_unit", canon: "m", fallback: [0, 100], optional: false },
  { key: "power", title: "Power", dimension: "power", skey: "power_ylim", ukey: "power_ylim_unit", canon: "kW", fallback: [0, 500], optional: false },
  { key: "efficiency", title: "Efficiency η", dimension: "efficiency", skey: "eff_ylim", ukey: "eff_ylim_unit", canon: "%", fallback: [0, 100], optional: false },
  { key: "npsh", title: "NPSHr", dimension: "npsh", skey: "npsh_ylim", ukey: "npsh_ylim_unit", canon: "m", fallback: [0, 10], optional: true },
];

const EMPTY: Settings = {};

function limitOf(s: Settings, key: string): [number, number] | null {
  const v = s[key];
  return Array.isArray(v) && v.length === 2 && v.every((x) => typeof x === "number")
    ? [v[0] as number, v[1] as number]
    : null;
}

/** The limit pair of one chart in canonical units (converted by Python); null while auto. */
function useCanonLimit(s: Settings, y: (typeof YLIMS)[number]): [number, number] | null {
  const lim = limitOf(s, y.skey);
  const unit = getStr(s, y.ukey, y.canon);
  const out = useConvertedMany(lim ?? [], unit, y.canon, y.dimension);
  if (!lim) return null;
  const [lo, hi] = out;
  return lo !== null && lo !== undefined && hi !== null && hi !== undefined && lo < hi
    ? [lo, hi]
    : null;
}

/** Performance Plot — mirrors pumpflow/nodes/performance_plot.py (UI_SPEC §5.5). */
export default function PerformancePlotForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const view = (result?.view ?? {}) as Partial<PerformancePlotView>;
  const rt = s ?? EMPTY;
  // fixed order: one hook per chart (the form is loading while `s` is null)
  const ylims: Partial<Record<PanelKey, [number, number] | null>> = {
    head: useCanonLimit(rt, YLIMS[0]!),
    power: useCanonLimit(rt, YLIMS[1]!),
    efficiency: useCanonLimit(rt, YLIMS[2]!),
    npsh: useCanonLimit(rt, YLIMS[3]!),
  };
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const show = {
    poly: getBool(s, "show_poly", true),
    spline: getBool(s, "show_spline", true),
    points: getBool(s, "show_points", true),
  };

  const setAuto = (y: (typeof YLIMS)[number], auto: boolean) => {
    const unit = getStr(s, y.ukey, y.canon);
    if (auto) {
      update(y.optional ? { [y.skey]: undefined } : { [y.skey]: null });
      return;
    }
    Promise.all(y.fallback.map((v) => engine.convert(v, y.canon, unit, y.dimension))).then(
      ([lo, hi]) =>
        update({ [y.skey]: [lo ?? y.fallback[0], hi ?? y.fallback[1]], [y.ukey]: unit }),
      () => undefined,
    );
  };

  const setLimit = (y: (typeof YLIMS)[number], which: 0 | 1, v: number | null, unit: string) => {
    const cur = limitOf(s, y.skey) ?? y.fallback;
    const oldUnit = getStr(s, y.ukey, y.canon);
    const put = (pair: [number, number]) => update({ [y.skey]: pair, [y.ukey]: unit });
    const next: [number, number] = [...cur];
    next[which] = v ?? 0;
    if (unit === oldUnit) {
      put(next);
      return;
    }
    // the unit changed: the field converted its own value, the other one follows
    const other = (1 - which) as 0 | 1;
    engine.convert(cur[other], oldUnit, unit, y.dimension).then(
      (o) => {
        next[other] = o ?? cur[other];
        put(next);
      },
      () => undefined,
    );
  };

  const hasFit = view.fit !== undefined;
  return (
    <div className="form-body">
      {hasFit && view.fit ? (
        <PerformanceChart
          fit={view.fit}
          rated={view.rated ?? null}
          npsh={view.npsh ?? null}
          show={show}
          ylims={ylims}
        />
      ) : (
        <Banner kind="info">{result?.status ?? "Waiting for fitted model"}</Banner>
      )}
      {error && <Banner kind="error">{error}</Banner>}
      <Divider />

      <Section title="Curves" />
      <Checkbox
        checked={show.poly}
        label="Polynomial curve"
        onChange={(v) => update({ show_poly: v })}
      />
      <Checkbox
        checked={show.spline}
        label="Spline (dashed)"
        onChange={(v) => update({ show_spline: v })}
      />
      <Checkbox
        checked={show.points}
        label="Data points"
        onChange={(v) => update({ show_points: v })}
      />
      <Divider />

      <Section title="Y-axis limits" />
      {YLIMS.map((y) => {
        const lim = limitOf(s, y.skey);
        const unit = getStr(s, y.ukey, y.canon);
        return (
          <div key={y.key} className="ylim-block">
            <Row label={y.title}>
              <Checkbox
                checked={lim === null}
                label={`${y.title} auto`}
                onChange={(auto) => setAuto(y, auto)}
              />
            </Row>
            <Row label={`${y.title} min`} disabled={lim === null}>
              <UnitField
                dimension={y.dimension}
                value={lim ? lim[0] : null}
                unit={unit}
                disabled={lim === null}
                onChange={(v, u) => setLimit(y, 0, v, u)}
              />
            </Row>
            <Row label={`${y.title} max`} disabled={lim === null}>
              <UnitField
                dimension={y.dimension}
                value={lim ? lim[1] : null}
                unit={unit}
                disabled={lim === null}
                onChange={(v, u) => setLimit(y, 1, v, u)}
              />
            </Row>
          </div>
        );
      })}
      <p className="field-hint">
        Untick auto to fix the limits of a chart; they start from a default range you can edit.
      </p>
    </div>
  );
}
