import { useLoaded } from "./useLoaded";
import { useEngine } from "./engineContext";
import { Banner, Divider, Row, Section, Select, TextField, UnitField, useConverted } from "./fields";
import type { FormProps } from "./forms.types";
import { getNum, getStr } from "./settings";
import { useNodeForm } from "./useNodeForm";

const SOURCES: Array<[string, string]> = [
  ["Manual (density + viscosity)", "manual"],
  ["Water at temperature", "water"],
];

/** Fluid — mirrors pumpflow/nodes/fluid.py (density chart: desktop only). */
export default function FluidForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const tempUnit = s ? getStr(s, "temp_unit", "°C") : "°C";
  const densUnit = s ? getStr(s, "dens_unit", "kg/m³") : "kg/m³";
  const tempC = useConverted(s ? getNum(s, "temp") : null, tempUnit, "°C", "temperature");
  const water = useLoaded(
    async (e) => (tempC === null ? null : await e.waterProperties(tempC)),
    null,
    String(tempC),
  );
  const dens = s ? getNum(s, "dens") : 0;
  const kg = useConverted(s ? dens : null, densUnit, "kg/m³", "density");
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const isWater = getStr(s, "source", "manual") === "water";
  const sg = kg === null ? null : kg / 1000;
  const dimension = (key: string, dim: string, fallback: string, densRel: number | null = null) => (
    <UnitField
      dimension={dim}
      value={getNum(s, key)}
      unit={getStr(s, `${key}_unit`, fallback)}
      densRel={densRel}
      onChange={(v, u) => update({ [key]: v ?? 0, [`${key}_unit`]: u })}
    />
  );

  return (
    <div className="form-body">
      <Section title="Fluid" />
      <Row label="Source">
        <Select value={getStr(s, "source", "manual")} options={SOURCES} onChange={(v) => update({ source: v })} />
      </Row>
      <Row label="Name">
        <TextField
          value={getStr(s, "name")}
          placeholder="e.g. Light Hydrocarbon"
          onChange={(v) => update({ name: v })}
        />
      </Row>
      <Divider />
      {isWater ? (
        <>
          <Row label="Temperature">{dimension("temp", "temperature", "°C")}</Row>
          <Row label="Density">
            <span className="readout">
              {water ? `${water.density.toFixed(3)} kg/m³  |  SG ${(water.density / 1000).toFixed(6)}` : "—"}
            </span>
          </Row>
          <Row label="Viscosity" suffix="cSt">
            <span className="readout">{water ? water.kinematic_cst.toFixed(6) : "—"}</span>
          </Row>
          <Row label="Dynamic viscosity" suffix="cP">
            <span className="readout">{water ? water.dynamic_cp.toFixed(6) : "—"}</span>
          </Row>
          <p className="field-hint">
            Density: 4th-order Kell polynomial in temperature. Viscosity: Andrade-type exponential,
            mu = 2.414e-5 * 10^(247.8 / (T[K] - 140)) Pa·s.
          </p>
          <p className="field-hint">
            References: Kell, G. S. (1975). Journal of Chemical and Engineering Data, 20(1), 97-105,
            doi:10.1021/je60064a005; Kestin, J., Sokolov, M., Wakeham, W. A. (1978). Journal of
            Physical and Chemical Reference Data, 7(3), 941-948, doi:10.1063/1.555581.
          </p>
        </>
      ) : (
        <>
          <Row label="Density">{dimension("dens", "density", "kg/m³")}</Row>
          <Row label="Relative density" suffix="SG">
            <span className="readout">{sg === null ? "—" : sg.toFixed(3)}</span>
          </Row>
          <Row label="Nominal viscosity">{dimension("visc", "viscosity", "cSt", sg)}</Row>
        </>
      )}
      {error && <Banner kind="error">{error}</Banner>}
      {result?.state === "invalid" && <Banner kind="error">{result.status}</Banner>}
    </div>
  );
}
