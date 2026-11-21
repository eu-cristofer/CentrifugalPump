import type { Dispatch } from "react";
import type { NodeResult, PumpflowDoc } from "../engine/types";
import type { Action } from "../project/store";

/** What FormPanel hands every form. */
export interface FormProps {
  nodeId: string;
  doc: PumpflowDoc;
  /** the node's last evaluation (undefined before the first one) */
  result: NodeResult | undefined;
  dispatch: Dispatch<Action>;
}
