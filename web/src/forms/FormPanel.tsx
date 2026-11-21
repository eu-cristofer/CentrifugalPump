import { type ComponentType, useEffect } from "react";
import { Pill, StateDot } from "../canvas/NodeCard";
import { statusBeside } from "../canvas/card";
import type { Dispatch } from "react";
import type { CatalogEntry, EvaluateResult, PumpflowDoc } from "../engine/types";
import { docNodes } from "../project/model";
import type { Action } from "../project/store";
import { EngineContext, type FormEngine } from "./engineContext";
import ComplianceForm from "./ComplianceForm";
import CorrectionForm from "./CorrectionForm";
import CurveFitForm from "./CurveFitForm";
import FluidForm from "./FluidForm";
import MrtCheckForm from "./MrtCheckForm";
import MrtLogForm from "./MrtLogForm";
import NoteForm from "./NoteForm";
import NpshForm from "./NpshForm";
import PerformancePlotForm from "./PerformancePlotForm";
import RatedPointForm from "./RatedPointForm";
import type { FormProps } from "./forms.types";
import TestPointsForm from "./TestPointsForm";
import "./forms.css";

/** Kinds with a web form (all witness kinds but report_export; the rest say "Edit this node in the desktop app."). */
export const FORMS: Record<string, ComponentType<FormProps>> = {
  rated_point: RatedPointForm,
  fluid: FluidForm,
  test_points: TestPointsForm,
  correction: CorrectionForm,
  curve_fit: CurveFitForm,
  compliance: ComplianceForm,
  performance_plot: PerformancePlotForm,
  npsh: NpshForm,
  mechanical_run: MrtLogForm,
  mechanical_run_check: MrtCheckForm,
  markdown_note: NoteForm,
};

export interface FormPanelProps {
  engine: FormEngine;
  doc: PumpflowDoc;
  catalog: CatalogEntry[];
  result: EvaluateResult | null;
  nodeId: string;
  dispatch: Dispatch<Action>;
  onClose: () => void;
}

/**
 * Right-side property panel of one node (420 px; full screen under 900 px).
 * Esc or × closes it.  Remounts per node so each form starts from its own settings.
 */
export default function FormPanel({
  engine,
  doc,
  catalog,
  result,
  nodeId,
  dispatch,
  onClose,
}: FormPanelProps) {
  const node = docNodes(doc).find((n) => n.id === nodeId);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (!node) return null;

  const entry = catalog.find((c) => c.kind === node.kind);
  const title = entry?.title ?? node.kind;
  const res = result?.nodes[nodeId];
  const state = res?.state ?? "idle";
  const badge = res?.badge ?? null;
  const Form = FORMS[node.kind];

  return (
    <aside className="form-panel" aria-label={`${title} form`}>
      <header className="form-title">
        <span className="node-glyph">{entry?.glyph ?? ""}</span>
        <span className="form-title-text">{title}</span>
        <span className="form-node-id">{nodeId}</span>
        <button type="button" className="form-close" aria-label="Close" onClick={onClose}>
          ×
        </button>
      </header>
      <div className="form-status">
        {badge ? <Pill text={badge[0]} tone={badge[1]} /> : <StateDot state={state} />}
        {(res?.notes ?? []).map((note) => (
          <Pill key={note} text={note} tone="warn" outline />
        ))}
        <span className={`status-text${state === "ok" ? " status-ok" : ""}`}>
          {statusBeside(res?.status ?? "", badge)}
        </span>
      </div>
      <div className="form-scroll">
        {Form ? (
          <EngineContext.Provider value={engine}>
            <Form key={nodeId} nodeId={nodeId} doc={doc} result={res} dispatch={dispatch} />
          </EngineContext.Provider>
        ) : (
          <p className="form-desktop-only">Edit this node in the desktop app.</p>
        )}
      </div>
    </aside>
  );
}
