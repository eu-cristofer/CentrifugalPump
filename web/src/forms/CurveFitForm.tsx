import PerformanceChart from "../charts/PerformanceChart";
import type { CurveFitView } from "../engine/types";
import { useEngine } from "./engineContext";
import { Banner, Checkbox, Divider, NumberField, Row, Section, Select } from "./fields";
import type { FormProps } from "./forms.types";
import { getBool, getNum } from "./settings";
import { useNodeForm } from "./useNodeForm";

const DEGREES: Array<[string, string]> = ["2", "3", "4", "5"].map((d) => [d, d]);
const RES_MIN = 40;
const RES_MAX = 400;

/** Curve Fit — mirrors pumpflow/nodes/curve_fit.py (UI_SPEC §5.4), with the preview chart. */
export default function CurveFitForm({ nodeId, doc, result, dispatch }: FormProps) {
  const engine = useEngine();
  const { runtime: s, update, error } = useNodeForm(engine, doc, nodeId, dispatch);
  const view = (result?.view ?? {}) as CurveFitView;
  if (!s) return <p className="form-loading">{error || "Loading…"}</p>;

  const fitted = result?.state === "ok" || result?.state === "reject";
  return (
    <div className="form-body">
      <Section title="Fit settings" />
      <Row label="Polynomial degree">
        <Select
          value={String(getNum(s, "degree", 3))}
          options={DEGREES}
          onChange={(v) => update({ degree: Number(v) })}
        />
      </Row>
      <Row label="">
        <Checkbox
          checked={getBool(s, "spline", true)}
          label="Overlay natural cubic spline"
          onChange={(v) => update({ spline: v })}
        />
      </Row>
      <Row label="Curve resolution" suffix="pts">
        <NumberField
          value={getNum(s, "resolution", 160)}
          onChange={(v) => {
            if (v !== null && Number.isInteger(v) && v >= RES_MIN && v <= RES_MAX) {
              update({ resolution: v });
            }
          }}
        />
      </Row>
      <Row label="">
        <p className="field-hint">{`${RES_MIN} to ${RES_MAX} points`}</p>
      </Row>
      {fitted && view.r2_text ? (
        <Banner kind="ok">{view.r2_text}</Banner>
      ) : (
        <Banner kind="info">{result?.status ?? ""}</Banner>
      )}
      {error && <Banner kind="error">{error}</Banner>}
      <Divider />

      <Section title="Coefficients (highest order first)" />
      <pre className="mono-block">{fitted ? (view.coeff_text ?? "") : ""}</pre>
      <Row label="">
        <Checkbox
          checked={getBool(s, "show_preview", true)}
          label="Show preview"
          onChange={(v) => update({ show_preview: v })}
        />
      </Row>
      {getBool(s, "show_preview", true) && fitted && view.points && view.poly && (
        <PerformanceChart
          fit={{
            points: view.points,
            poly: view.poly,
            spline: getBool(s, "spline", true) ? (view.spline ?? null) : null,
            ...(view.degree !== undefined ? { degree: view.degree } : {}),
          }}
          show={{ poly: true, spline: getBool(s, "spline", true), points: true }}
        />
      )}
    </div>
  );
}
