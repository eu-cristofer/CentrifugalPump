import { useEffect, useRef, useState } from "react";
import { fixed } from "../decimal";
import type { RatedPointView } from "../engine/types";
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
  useConverted,
} from "./fields";
import type { FormProps } from "./forms.types";
import { getBool, getNum, getNumOrNull, getStr } from "./settings";
import { useLoaded } from "./useLoaded";
import { useNodeForm } from "./useNodeForm";

const DEFAULT_FLUID = "__default__";
const DEFAULT_LABEL = "Custom (entered below)";

/** Rated Point Input — mirrors pumpflow/nodes/rated_point.py (UI_SPEC §5.1, §12). */
export default function RatedPointForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const view = (result?.view ?? {}) as Partial<RatedPointView> & {
    standard_key?: string;
    client?: string;
  };
  const standards = useLoaded((e) => e.standards(), [] as Array<[string, string]>);
  const clients = useLoaded((e) => e.clients(), [] as Array<[string, string]>);
  const pumpTypes = useLoaded((e) => e.pumpTypes(), [] as Array<[string, string]>);
  const waterRef = useLoaded((e) => e.waterDensity(20), null as number | null);
  const pumpType = s ? getStr(s, "pump_type") : "";
  const typeHint = useLoaded((e) => e.pumpTypeHint(pumpType), "", pumpType);

  // Density: shown in `dens_unit`, stored as relative density (kept in sync).
  const densRel = s ? getNum(s, "dens_rel") : 0;
  const densUnit = s ? getStr(s, "dens_unit", "kg/m³") : "kg/m³";
  const fromRel = useConverted(densRel * 1000, "kg/m³", densUnit, "density");
  const [densShown, setDensShown] = useState<number | null>(null);
  const selfEdit = useRef(false);
  useEffect(() => {
    if (selfEdit.current) {
      selfEdit.current = false;
      return;
    }
    if (fromRel !== null) setDensShown(fromRel);
  }, [fromRel]);

  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const override = view.override ?? null;
  const fluids = view.fluids ?? [];
  const num = (key: string) => getNum(s, key);
  const unit = (key: string, fallback: string) => getStr(s, `${key}_unit`, fallback);
  const dim = (
    key: string,
    dimension: string,
    fallback: string,
    opts: { optional?: boolean; densRel?: number } = {},
  ) => (
    <UnitField
      dimension={dimension}
      value={opts.optional ? getNumOrNull(s, key) : num(key)}
      unit={unit(key, fallback)}
      densRel={opts.densRel ?? null}
      onChange={(v, u) =>
        update({
          [key]: opts.optional ? (v !== null && v > 0 ? v : null) : (v ?? 0),
          [`${key}_unit`]: u,
        })
      }
    />
  );

  const standardKey = getStr(s, "standard_key") || view.standard_key || "api610:12";
  const client = s["client"] === undefined ? (view.client ?? "") : getStr(s, "client");
  const changeStandard = (key: string, cl: string) => {
    update({ standard_key: key, client: cl });
    engine.standardLabel(key, cl || null).then(
      (label) => update({ standard: label }),
      () => undefined,
    );
  };

  const kgFromDisplay = async (v: number | null, u: string) => {
    const kg = v === null ? 0 : await engine.convert(v, u, "kg/m³", "density");
    selfEdit.current = true;
    setDensShown(v);
    update({ dens_rel: (kg ?? 0) / 1000, dens_unit: u });
  };

  const fluidLocked = override !== null;
  const relShown = override ? override.density_rel : densRel;
  const kgShown = override ? (override.density_kgm3 ?? 0) : densRel * 1000;

  return (
    <div className="form-body">
      <Section title="Identification" />
      <Row label="Service">
        <TextField
          value={getStr(s, "service")}
          placeholder="e.g. Crude Oil Transfer"
          onChange={(v) => update({ service: v })}
        />
      </Row>
      <Row label="Service TAG">
        <TextField
          value={getStr(s, "tag")}
          placeholder="service / datasheet TAG"
          onChange={(v) => update({ tag: v })}
        />
      </Row>
      <Row label="Standard / edition">
        <Select
          value={standardKey}
          options={standards.map(([key, label]): [string, string] => [label, key])}
          onChange={(key) => changeStandard(key, client)}
        />
      </Row>
      <Row label="Client overlay">
        <Select
          value={client}
          options={[["None", ""], ...clients.map(([c, label]): [string, string] => [label, c])]}
          onChange={(c) => changeStandard(standardKey, c)}
        />
      </Row>
      <Row label="Label on report cover">
        <TextField
          value={getStr(s, "standard")}
          onChange={(v) => update({ standard: v })}
        />
      </Row>

      <Section title="API 610 pump type" info="pump_type" />
      <Row label="Pump type">
        <Select
          value={pumpType}
          options={[
            ["— not set —", ""],
            ...pumpTypes.map(([code, desc]): [string, string] => [`${code} — ${desc}`, code]),
          ]}
          onChange={(code) => update({ pump_type: code === "" ? undefined : code })}
        />
      </Row>
      <Row label="">
        <p className="field-hint">{typeHint}</p>
      </Row>
      <Divider />

      <Section title="Rated duty" />
      <Row label="Capacity Q">{dim("q", "capacity", "m³/h")}</Row>
      <Row label="Diff. head H">{dim("head", "head", "m")}</Row>
      <Row label="Speed N">{dim("n", "speed", "rpm")}</Row>
      <Row label="Power P">{dim("power", "power", "kW")}</Row>
      <Row label="Efficiency η">{dim("eff", "efficiency", "%")}</Row>
      <Row label="Shut-off head">{dim("head_shutoff", "head", "m")}</Row>
      <Row label="NPSHa">{dim("npsha", "npsh", "m")}</Row>
      <Divider />

      <Section title="Impeller diameter (datasheet, 0 = not set)" info="impeller_diameter" />
      <Row label="Nominal D">{dim("d_imp", "length", "mm", { optional: true })}</Row>
      <Row label="Maximum D">{dim("d_max", "length", "mm", { optional: true })}</Row>
      <Row label="Minimum D">{dim("d_min", "length", "mm", { optional: true })}</Row>
      <Divider />

      <Section title="Rated fluid" />
      {fluids.length > 0 && (
        <Row label="Fluid source">
          <Select
            value={view.choice ?? DEFAULT_FLUID}
            options={[[DEFAULT_LABEL, DEFAULT_FLUID], ...fluids.map((f): [string, string] => [f, f])]}
            onChange={(v) => update({ fluid_choice: v })}
          />
        </Row>
      )}
      <Row label="Fluid name">
        <TextField
          value={getStr(s, "fluid_name", "Rated fluid")}
          placeholder="e.g. Light Hydrocarbon"
          disabled={fluidLocked}
          onChange={(v) => update({ fluid_name: v })}
        />
      </Row>
      {!fluidLocked && (
        <>
          <Row label="Relative density input" suffix="SG">
            <NumberField value={densRel} onChange={(v) => update({ dens_rel: v ?? 0 })} />
          </Row>
          <Row label="Density input">
            <UnitField
              dimension="density"
              value={densShown}
              unit={densUnit}
              onChange={(v, u) => void kgFromDisplay(v, u)}
            />
          </Row>
        </>
      )}
      <Row label="Relative density" suffix="SG">
        <span className="readout">{fixed(relShown, 6)}</span>
      </Row>
      <Row label="Density" suffix="kg/m³">
        <span className="readout">{fixed(kgShown, 3)}</span>
      </Row>
      <Row label="Nominal viscosity">
        {dim("visc", "viscosity", "cSt", { densRel })}
      </Row>
      <Row label="Water reference">
        <span className="readout">
          {override
            ? "From connected Fluid node"
            : waterRef === null
              ? "…"
              : `Water @ 20 °C = ${fixed(waterRef, 3)} kg/m³`}
        </span>
      </Row>
      <Row label="">
        <Checkbox
          checked={getBool(s, "parallel")}
          label="Parallel-operation unit (A/B)"
          onChange={(v) => update({ parallel: v })}
        />
      </Row>

      {error && <Banner kind="error">{error}</Banner>}
      {result?.state === "invalid" && <Banner kind="error">{result.status}</Banner>}
      {override && <Banner kind="info">{`Rated fluid from wired Fluid node: ${override.name}.`}</Banner>}
    </div>
  );
}
