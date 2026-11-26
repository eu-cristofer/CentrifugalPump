import type { CorrectionView } from "../engine/types";
import { fixed } from "../decimal";
import { useEngine } from "./engineContext";
import {
  Banner,
  Checkbox,
  Divider,
  InfoButton,
  Row,
  Section,
  Select,
  UnitField,
  useConvertedMany,
  useUnitOptions,
} from "./fields";
import type { FormProps } from "./forms.types";
import { getBool, getNum, getStr } from "./settings";
import { useNodeForm } from "./useNodeForm";

const DEFAULT_FLUID = "__default__";
const DEFAULT_LABEL = "Rated fluid";
const DEGREES: Array<[string, string]> = ["2", "3", "4", "5"].map((d) => [d, d]);

/** Dimensions of the before/after table and the units its values arrive in. */
const TABLE_DIMS: Array<{ dim: string; label: string; canonical: string }> = [
  { dim: "capacity", label: "Q", canonical: "m³/h" },
  { dim: "head", label: "Head", canonical: "m" },
  { dim: "power", label: "Power", canonical: "kW" },
];

const show = (v: number | null | undefined, decimals = 2): string => fixed(v, decimals);

function TableUnit({
  dimension,
  label,
  unit,
  onPick,
}: {
  dimension: string;
  label: string;
  unit: string;
  onPick: (unit: string) => void;
}) {
  const options = useUnitOptions(dimension);
  return (
    <Select
      value={unit}
      options={options.map(([l]): [string, string] => [l, l])}
      ariaLabel={`Show ${label} in`}
      onChange={onPick}
    />
  );
}

/** Speed / Affinity Correction — mirrors pumpflow/nodes/correction.py (UI_SPEC §5.3). */
export default function CorrectionForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const view = (result?.view ?? {}) as Partial<CorrectionView>;
  const pairs = view.before_after ?? [];
  const stored =
    s && s.table_units && typeof s.table_units === "object"
      ? (s.table_units as Record<string, string>)
      : {};
  const unitFor = (dim: string, canonical: string) => stored[dim] ?? canonical;
  const measured = pairs.map((p) => p.measured);
  const corrected = pairs.map((p) => p.corrected);
  // fixed hook order: (measured, corrected) x (capacity, head, power)
  const mQ = useConvertedMany(measured.map((r) => r.q), "m³/h", unitFor("capacity", "m³/h"), "capacity");
  const cQ = useConvertedMany(corrected.map((r) => r.q), "m³/h", unitFor("capacity", "m³/h"), "capacity");
  const mH = useConvertedMany(measured.map((r) => r.head), "m", unitFor("head", "m"), "head");
  const cH = useConvertedMany(corrected.map((r) => r.head), "m", unitFor("head", "m"), "head");
  const mP = useConvertedMany(measured.map((r) => r.power), "kW", unitFor("power", "kW"), "power");
  const cP = useConvertedMany(corrected.map((r) => r.power), "kW", unitFor("power", "kW"), "power");
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const hasRated = view.has_rated ?? true;
  const hasFluid = view.has_fluid ?? false;
  const lock = getBool(s, "lock_to_rated", true);
  const applyDensity = getBool(s, "apply_density", true);
  const densityOk = hasRated || hasFluid;
  const fluids = view.fluids ?? [];
  const banner = view.banner;
  const unitsPicked = TABLE_DIMS.map((d) => unitFor(d.dim, d.canonical));

  return (
    <div className="form-body">
      <Section title="Target & corrections" />
      <Row label="Target speed" disabled={lock && hasRated}>
        <UnitField
          dimension="speed"
          value={getNum(s, "target_speed", 1750)}
          unit={getStr(s, "target_speed_unit", "rpm")}
          disabled={lock && hasRated}
          onChange={(v, u) => update({ target_speed: v ?? 0, target_speed_unit: u })}
        />
      </Row>
      <Row label="">
        <Checkbox
          checked={lock}
          disabled={!hasRated}
          label="Lock target speed to rated N"
          onChange={(v) => update({ lock_to_rated: v })}
        />
      </Row>
      <Row label="">
        <Checkbox
          checked={getBool(s, "apply_speed", true)}
          label="Speed (affinity) correction"
          onChange={(v) => update({ apply_speed: v })}
        />
      </Row>
      <Row label="">
        <Checkbox
          checked={applyDensity}
          disabled={!densityOk}
          label="Density (ρ_rated / ρ_test) correction"
          onChange={(v) => update({ apply_density: v })}
        />
      </Row>
      <Row label="">
        <Checkbox
          checked={getBool(s, "apply_viscosity")}
          disabled={!(applyDensity && densityOk)}
          label="Viscosity correction (HI 9.6.7)"
          onChange={(v) => update({ apply_viscosity: v })}
        />
      </Row>
      <Row label="HI 9.6.7 factors">
        <span className="readout">{view.viscous_text ?? "—"}</span>
        <InfoButton infoKey="viscosity_b" />
      </Row>
      <Row label="Fit degree">
        <Select
          value={String(getNum(s, "degree", 3))}
          options={DEGREES}
          onChange={(v) => update({ degree: Number(v) })}
        />
      </Row>
      {fluids.length > 0 && (
        <Row label="Correct to fluid">
          <Select
            value={view.choice ?? DEFAULT_FLUID}
            options={[[DEFAULT_LABEL, DEFAULT_FLUID], ...fluids.map((f): [string, string] => [f, f])]}
            onChange={(v) => update({ fluid_choice: v })}
          />
        </Row>
      )}
      <Divider />

      <Section title="Before / after correction" />
      <div className="tool-bar">
        {TABLE_DIMS.map((d, i) => (
          <span key={d.dim} className="tool-bar">
            <span className="row-label">{d.label}</span>
            <TableUnit
              dimension={d.dim}
              label={d.label}
              unit={unitsPicked[i]!}
              onPick={(u) =>
                update({
                  table_units: Object.fromEntries(
                    TABLE_DIMS.map((x, j) => [x.dim, x.dim === d.dim ? u : unitsPicked[j]]),
                  ),
                })
              }
            />
          </span>
        ))}
      </div>
      <div className="grid-wrap">
        <table className="grid" aria-label="Before / after correction">
          <thead>
            <tr>
              <th>{`Q [${unitsPicked[0]}]`}</th>
              <th>{`Head [${unitsPicked[1]}]`}</th>
              <th>{`Power [${unitsPicked[2]}]`}</th>
              <th>η [%]</th>
              <th className="grid-text">stage</th>
            </tr>
          </thead>
          <tbody>
            {pairs.flatMap((p, i) => [
              <tr key={`m${i}`}>
                <td>{show(mQ[i])}</td>
                <td>{show(mH[i])}</td>
                <td>{show(mP[i])}</td>
                <td>{show(p.measured.eff, 1)}</td>
                <td className="grid-text v-info">measured</td>
              </tr>,
              <tr key={`c${i}`}>
                <td>{show(cQ[i])}</td>
                <td>{show(cH[i])}</td>
                <td>{show(cP[i])}</td>
                <td>{show(p.corrected.eff, 1)}</td>
                <td className="grid-text">corrected</td>
              </tr>,
            ])}
          </tbody>
        </table>
      </div>
      {error && <Banner kind="error">{error}</Banner>}
      {banner && banner.text && <Banner kind={banner.level}>{banner.text}</Banner>}
      {!banner && result?.state === "invalid" && <Banner kind="error">{result.status}</Banner>}
    </div>
  );
}
